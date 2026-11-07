"""
The rules for job posts. The website views and the app API both call these
functions - never the models directly - so the two can never disagree.

Each action raises VacancyError(message) when it is not allowed; the message
is safe to show to the user.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .chat_access import is_admin
from .vacancy_models import EmploymentContract, Vacancy, VacancyApplication

logger = logging.getLogger(__name__)

ALERT_LIMIT = 300  # workers told about one new job at most
REMIND_DAYS = 7    # "your contract ends in a week"


class VacancyError(Exception):
    pass


# --------------------------------------------------------------------- who

def worker_profile(user):
    return getattr(user, 'worker_profile', None) if getattr(user, 'user_type', '') == 'worker' else None


def can_post(user):
    return bool(user.is_authenticated and user.is_active and getattr(user, 'user_type', '') == 'client')


def can_manage(user, vacancy):
    """The poster or an admin: shortlist, hire, close."""
    return bool(user.is_authenticated and (is_admin(user) or vacancy.poster_id == user.id))


def type_matches(profile, vacancy):
    return vacancy.worker_type_needed == 'any' or profile.worker_type == vacancy.worker_type_needed


def hired_on(user, vacancy):
    """True if this worker holds a place on this job (contract running or finished
    normally). Once a contract is ended early the application becomes 'ended',
    which closes it for every period of that hire, renewals included."""
    profile = worker_profile(user)
    return bool(profile and vacancy.applications.filter(worker=profile, status='hired').exists())


def relationship_open(contract):
    """Chat, call, phone numbers and the address stay available for this hire."""
    return contract.application.status == 'hired' and contract.status != 'ended_early'


def with_counts(qs):
    """Annotate places / applicant counts so lists don't run a query per row.
    Django drops Meta.ordering on grouped queries, so keep newest-first unless
    the caller already chose an order (otherwise pages repeat or skip rows)."""
    qs = qs.annotate(
        hired_n=Count('applications', filter=Q(applications__status='hired'), distinct=True),
        applicant_n=Count('applications', filter=~Q(applications__status='withdrawn'), distinct=True))
    return qs if qs.query.order_by else qs.order_by('-created_at', '-id')


def attach_counts(vacancies):
    """Same counts for vacancies loaded through a relation (one query for all)."""
    vacancies = [v for v in vacancies if v is not None]
    ids = {v.pk for v in vacancies}
    if not ids:
        return
    rows = with_counts(Vacancy.objects.filter(pk__in=ids)).values('pk', 'hired_n', 'applicant_n')
    by_id = {r['pk']: r for r in rows}
    for v in vacancies:
        v.hired_n = by_id[v.pk]['hired_n']
        v.applicant_n = by_id[v.pk]['applicant_n']


def can_view(user, vacancy):
    if not user.is_authenticated:
        return False
    if can_manage(user, vacancy):
        return True
    profile = worker_profile(user)
    if profile is None:
        return False
    if vacancy.applications.filter(worker=profile).exists():
        return True  # their own application stays visible after the job closes
    return vacancy.status == 'published'


def sees_private_details(user, vacancy):
    """Exact address and the poster's phone: only the admin, the poster, and hired workers."""
    return can_manage(user, vacancy) or hired_on(user, vacancy)


def apply_problem(user, vacancy):
    """Why this user cannot apply right now, or None if they can."""
    profile = worker_profile(user)
    if profile is None:
        return 'Only workers can apply for jobs.'
    if not user.is_active:
        return 'Your account is not active.'
    if profile.verification_status != 'verified':
        return 'Only verified workers can apply. Upload your ID so our team can verify you.'
    if not type_matches(profile, vacancy):
        return f'This job is for {vacancy.get_worker_type_needed_display()} workers.'
    if not vacancy.is_open:
        return 'This job is no longer taking applications.'
    existing = vacancy.applications.filter(worker=profile).first()
    if existing and existing.status != 'withdrawn':
        return 'You have already applied for this job.'
    return None


# --------------------------------------------------------------------- lists

def published_open():
    return with_counts(Vacancy.objects.filter(status='published', closing_date__gte=timezone.localdate())
                       .select_related('category', 'poster'))


def jobs_for_worker(user, params=None):
    """Published, still-open jobs. Filters: category, city, duration, kind, q, only_mine (my type)."""
    params = params or {}
    qs = published_open()
    if str(params.get('category') or '').isdigit():
        qs = qs.filter(category_id=int(params['category']))
    if params.get('city'):
        qs = qs.filter(city__icontains=params['city'])
    if params.get('duration'):
        qs = qs.filter(duration=params['duration'])
    if params.get('kind') in ('home', 'business'):
        qs = qs.filter(kind=params['kind'])
    if params.get('q'):
        q = params['q']
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))
    profile = worker_profile(user)
    if profile is not None and params.get('only_mine') in ('1', 'true', 'on', True):
        qs = qs.filter(worker_type_needed__in=['any', profile.worker_type])
    return qs.order_by('-published_at', '-created_at')


# --------------------------------------------------------------------- poster

def submit(user, form):
    """A client sends a new job post for review."""
    if not can_post(user):
        raise VacancyError('Only clients can post jobs.')
    vacancy = form.save(commit=False)
    vacancy.poster = user
    vacancy.status = 'review'
    vacancy.save()
    _notify_admins_to_review(vacancy)
    return vacancy


def resubmit(user, vacancy, form):
    """The poster edits a post that is under review, sent back or rejected - it goes back for review."""
    if vacancy.poster_id != user.id:
        raise VacancyError('You can only edit your own job posts.')
    if vacancy.status not in ('review', 'changes', 'rejected'):
        raise VacancyError('A published job cannot be edited. Close it and post a new one.')
    vacancy = form.save(commit=False)
    vacancy.status = 'review'
    vacancy.save()
    _notify_admins_to_review(vacancy)
    return vacancy


def close(user, vacancy):
    if not can_manage(user, vacancy):
        raise VacancyError('You cannot close this job.')
    if vacancy.status not in ('published', 'review', 'changes'):
        raise VacancyError('This job is already closed.')
    with transaction.atomic():
        vacancy.status = 'closed'
        vacancy.save(update_fields=['status', 'updated_at'])
        _turn_down_the_rest(vacancy, user)
    return vacancy


# --------------------------------------------------------------------- admin

def review(admin, vacancy, action, note=''):
    if not is_admin(admin):
        raise VacancyError('Only the admin team reviews job posts.')
    if vacancy.status not in ('review', 'changes'):
        raise VacancyError('This job post is not waiting for review.')
    now = timezone.now()
    vacancy.reviewed_by, vacancy.reviewed_at, vacancy.review_note = admin, now, (note or '').strip()
    if action == 'publish':
        if vacancy.closing_date < timezone.localdate():
            raise VacancyError('The closing date has passed - ask the poster for a new date.')
        vacancy.status, vacancy.published_at = 'published', now
    elif action == 'changes':
        vacancy.status = 'changes'
    elif action == 'reject':
        vacancy.status = 'rejected'
    else:
        raise VacancyError('Unknown action.')
    vacancy.save()
    _notify(vacancy.poster, {
        'publish': ('Your job is published', f'"{vacancy.title}" is now visible to workers.'),
        'changes': ('Changes needed on your job post', f'"{vacancy.title}": {vacancy.review_note}'),
        'reject': ('Your job post was not approved', f'"{vacancy.title}": {vacancy.review_note}'),
    }[action], 'job_accepted' if action == 'publish' else 'job_rejected', vacancy=vacancy)
    if action == 'publish':
        alert_matching_workers(vacancy)
    return vacancy


def matching_workers(vacancy):
    from workers.models import WorkerProfile
    qs = WorkerProfile.objects.filter(verification_status='verified', user__is_active=True)
    if vacancy.category_id:
        qs = qs.filter(categories=vacancy.category_id)
    qs = qs.filter(Q(city__iexact=vacancy.city) | Q(can_work_everywhere=True))
    if vacancy.worker_type_needed != 'any':
        qs = qs.filter(worker_type=vacancy.worker_type_needed)
    return qs.select_related('user').distinct()[:ALERT_LIMIT]


def alert_matching_workers(vacancy):
    """Tell verified workers in that trade and city. No email - this can be hundreds of people."""
    sent = 0
    where = f'{vacancy.area}, {vacancy.city}' if vacancy.area else vacancy.city
    for profile in matching_workers(vacancy):
        _notify(profile.user, ('New job for you', f'{vacancy.title} - {where}, {vacancy.get_duration_display()}'),
                'system_alert', vacancy=vacancy, send_email=False)
        sent += 1
    return sent


# --------------------------------------------------------------------- worker

def apply(user, vacancy, message=''):
    with transaction.atomic():
        vacancy = Vacancy.objects.select_for_update().get(pk=vacancy.pk)
        problem = apply_problem(user, vacancy)
        if problem:
            raise VacancyError(problem)
        profile = worker_profile(user)
        app, created = VacancyApplication.objects.get_or_create(
            vacancy=vacancy, worker=profile, defaults={'message': message})
        if not created:  # re-applying after withdrawing
            app.status, app.message, app.decided_at, app.decided_by = 'applied', message, None, None
            app.save()
    _notify(vacancy.poster, ('New applicant', f'{user.get_full_name() or "A worker"} applied for "{vacancy.title}".'),
            'job_application', vacancy=vacancy, application=app)
    return app


def withdraw(user, app):
    if worker_profile(user) is None or app.worker.user_id != user.id:
        raise VacancyError('This is not your application.')
    with transaction.atomic():
        # re-read under a lock: the poster may be hiring this worker right now
        app = VacancyApplication.objects.select_for_update().get(pk=app.pk)
        if app.status not in VacancyApplication.ACTIVE:
            raise VacancyError('This application can no longer be withdrawn.')
        app.status = 'withdrawn'
        app.save(update_fields=['status', 'updated_at'])
    return app


# --------------------------------------------------------------------- choosing

def _decide(user, app, status):
    if not can_manage(user, app.vacancy):
        raise VacancyError('Only the poster or the admin team can decide on applicants.')
    with transaction.atomic():
        locked = VacancyApplication.objects.select_for_update().get(pk=app.pk)
        if locked.status not in VacancyApplication.ACTIVE:
            raise VacancyError('This applicant has already been decided on.')
        locked.status, locked.decided_by, locked.decided_at = status, user, timezone.now()
        locked.save(update_fields=['status', 'decided_by', 'decided_at', 'updated_at'])
    app.status = status


def shortlist(user, app):
    _decide(user, app, 'shortlisted')
    _notify(app.worker.user, ('You are shortlisted', f'You are on the shortlist for "{app.vacancy.title}".'),
            'job_accepted', vacancy=app.vacancy, application=app)
    return app


def turn_down(user, app):
    _decide(user, app, 'not_selected')
    _notify(app.worker.user, ('Application update', f'You were not selected for "{app.vacancy.title}".'),
            'job_rejected', vacancy=app.vacancy, application=app)
    return app


def hire(user, app, start_date=None, terms=''):
    with transaction.atomic():
        vacancy = Vacancy.objects.select_for_update().get(pk=app.vacancy_id)
        app = VacancyApplication.objects.select_for_update().get(pk=app.pk)
        if not can_manage(user, vacancy):
            raise VacancyError('Only the poster or the admin team can hire.')
        if vacancy.status != 'published':
            raise VacancyError('This job is not open any more.')
        if app.status not in VacancyApplication.ACTIVE:
            raise VacancyError('This applicant has already been decided on.')
        if vacancy.places_left <= 0:
            raise VacancyError('All places for this job are already filled.')
        if app.worker.verification_status != 'verified' or not app.worker.user.is_active:
            raise VacancyError('This worker is not verified any more.')
        if start_date and start_date < timezone.localdate():
            raise VacancyError('The start date cannot be in the past.')
        start = start_date or max(vacancy.start_date, timezone.localdate())
        app.status, app.decided_by, app.decided_at = 'hired', user, timezone.now()
        app.save()
        contract = EmploymentContract.objects.create(
            application=app, vacancy=vacancy, worker=app.worker, employer=vacancy.poster,
            start_date=start, end_date=vacancy.contract_end_date(start),
            salary_amount=vacancy.salary_amount, pay_period=vacancy.pay_period, terms=terms or '')
        app.worker.availability = 'busy'
        app.worker.save(update_fields=['availability'])
        filled = vacancy.places_left <= 0
        if filled:
            vacancy.status = 'filled'
            vacancy.save(update_fields=['status', 'updated_at'])
    _notify(app.worker.user, ('You are hired!', f'You got the job "{vacancy.title}". You can now chat and call.'),
            'job_accepted', vacancy=vacancy, application=app, contract=contract)
    if vacancy.poster_id != user.id:  # the admin hired on the poster's behalf
        _notify(vacancy.poster, ('Worker hired', f'{app.worker.user.get_full_name()} was hired for "{vacancy.title}".'),
                'job_accepted', vacancy=vacancy, contract=contract)
    if filled:
        _turn_down_the_rest(vacancy, user)
    return contract


def _turn_down_the_rest(vacancy, user):
    for app in vacancy.applications.filter(status__in=VacancyApplication.ACTIVE).select_related('worker__user'):
        app.status, app.decided_by, app.decided_at = 'not_selected', user, timezone.now()
        app.save()
        _notify(app.worker.user, ('Application update', f'"{vacancy.title}" is now closed. You were not selected.'),
                'job_rejected', vacancy=vacancy, application=app)


# --------------------------------------------------------------------- contracts

def contract_party(user, contract):
    """'employer', 'worker', 'admin' or None."""
    if not user.is_authenticated:
        return None
    if is_admin(user):
        return 'admin'
    if contract.employer_id == user.id:
        return 'employer'
    if contract.worker.user_id == user.id:
        return 'worker'
    return None


def end_contract(user, contract, reason):
    party = contract_party(user, contract)
    if party is None:
        raise VacancyError('This is not your contract.')
    if not (reason or '').strip():
        raise VacancyError('Please give a reason.')
    reopened = False
    with transaction.atomic():
        contract = (EmploymentContract.objects.select_for_update()
                    .select_related('vacancy', 'worker__user', 'employer', 'application').get(pk=contract.pk))
        if contract.status != 'active':
            raise VacancyError('This contract has already ended.')
        # a fixed-term contract ended before its date is "ended early"; ending a
        # permanent job (notice, resignation) is a normal finish
        early = contract.end_date is not None and timezone.localdate() < contract.end_date
        contract.status = 'ended_early' if early else 'finished'
        contract.end_reason, contract.ended_by, contract.ended_at = reason.strip(), user, timezone.now()
        contract.save()
        if early:
            # closes chat / contact for every period of this hire, and gives the place back
            app = contract.application
            app.status = 'ended'
            app.save(update_fields=['status', 'updated_at'])
            v = Vacancy.objects.select_for_update().get(pk=contract.vacancy_id)
            if v.status == 'filled' and v.closing_date >= timezone.localdate():
                v.status = 'published'
                v.save(update_fields=['status', 'updated_at'])
                reopened = True
    _free_worker(contract.worker)
    if reopened:
        _notify(contract.employer, ('A place is open again',
                                    f'"{contract.vacancy.title}" is taking applications again.'),
                'system_alert', vacancy=contract.vacancy)
    who = user.get_full_name() or 'The other side'
    for other in _other_parties(contract, user):
        _notify(other, ('Contract ended', f'{who} ended the contract for "{contract.vacancy.title}": {contract.end_reason}'),
                'job_completed', contract=contract)
    return contract


def renew(user, contract, duration):
    """A new contract period for the same worker, starting when this one ends."""
    party = contract_party(user, contract)
    if party not in ('employer', 'admin'):
        raise VacancyError('Only the employer or the admin team can renew a contract.')
    duration = duration if isinstance(duration, str) else ''
    if duration != 'permanent' and duration not in Vacancy.DURATION_DAYS:
        raise VacancyError('Choose how long to renew for.')
    days = Vacancy.DURATION_DAYS.get(duration)
    with transaction.atomic():
        contract = (EmploymentContract.objects.select_for_update()
                    .select_related('vacancy', 'worker__user', 'employer', 'application').get(pk=contract.pk))
        if contract.status not in ('active', 'finished') or contract.application.status != 'hired':
            raise VacancyError('This contract cannot be renewed.')
        if EmploymentContract.objects.filter(renewed_from=contract).exists():
            raise VacancyError('This contract was already renewed.')
        start = max(contract.end_date or timezone.localdate(), timezone.localdate())
        contract.status, contract.ended_by, contract.ended_at = 'renewed', user, timezone.now()
        contract.save()
        new = EmploymentContract.objects.create(
            application=contract.application, vacancy=contract.vacancy, worker=contract.worker,
            employer=contract.employer, start_date=start,
            end_date=(start + timedelta(days=days)) if days else None,
            salary_amount=contract.salary_amount, pay_period=contract.pay_period,
            terms=contract.terms, renewed_from=contract)
        contract.worker.availability = 'busy'
        contract.worker.save(update_fields=['availability'])
    for other in _other_parties(new, user):
        _notify(other, ('Contract renewed', f'The contract for "{new.vacancy.title}" was renewed.'),
                'job_accepted', contract=new)
    return new


def rate(user, contract, rating, feedback=''):
    party = contract_party(user, contract)
    if party not in ('employer', 'worker'):
        raise VacancyError('Only the employer and the worker rate each other.')
    if contract.status == 'active':
        raise VacancyError('You can rate once the contract has ended.')
    if not 1 <= int(rating) <= 5:
        raise VacancyError('Choose 1 to 5 stars.')
    field = 'employer_rating' if party == 'employer' else 'worker_rating'
    with transaction.atomic():
        contract = EmploymentContract.objects.select_for_update().get(pk=contract.pk)
        if getattr(contract, field):
            raise VacancyError('You have already rated this contract.')
        setattr(contract, field, int(rating))
        setattr(contract, 'employer_feedback' if party == 'employer' else 'worker_feedback',
                (feedback or '').strip())
        contract.save()
    return contract


def report(user, obj, report_type, description):
    """Report a job post or a contract to the admin team."""
    from .models import Report
    if isinstance(obj, Vacancy):
        if not can_view(user, obj):
            raise VacancyError('Job not found.')
        kind, reported = 'job', obj.poster
    else:
        party = contract_party(user, obj)
        if party in (None, 'admin'):
            raise VacancyError('This is not your contract.')
        kind = 'contract'
        reported = obj.worker.user if party == 'employer' else obj.employer
    rep = Report.objects.create(reporter=user, reported_user=reported, content_type=kind, content_id=obj.pk,
                                report_type=report_type, description=(description or '').strip())
    _notify_admins(('New report', f'{user.get_full_name() or user.username} reported a {kind}.'),
                   extra={'report_id': rep.pk, f'{"vacancy" if kind == "job" else "contract"}_id': obj.pk})
    return rep


def _other_parties(contract, user):
    people = [contract.employer, contract.worker.user]
    return [p for p in people if p.pk != user.pk]


def _free_worker(profile):
    """Back to 'available' when nothing else keeps them busy."""
    from .service_request_models import ServiceRequestAssignment
    busy = (EmploymentContract.objects.filter(worker=profile, status='active').exists()
            or ServiceRequestAssignment.objects.filter(worker=profile, status__in=('accepted', 'in_progress')).exists())
    if not busy and profile.availability == 'busy':
        profile.availability = 'available'
        profile.save(update_fields=['availability'])


# --------------------------------------------------------------------- daily

def daily_maintenance(today=None):
    """Close jobs past their closing date, finish contracts past their end date,
    and remind both sides a week before a contract ends. Safe to run often."""
    today = today or timezone.localdate()
    closed = finished = reminded = 0
    for v in Vacancy.objects.filter(status='published', closing_date__lt=today):
        v.status = 'closed'
        v.save(update_fields=['status', 'updated_at'])
        closed += 1
        hired = v.hired_count
        _notify(v.poster, ('Applications closed', f'"{v.title}" closed: {hired} of {v.workers_needed} hired.'),
                'system_alert', vacancy=v)
        _turn_down_the_rest(v, v.poster)
    for c in EmploymentContract.objects.filter(status='active', end_date__lt=today).select_related('worker__user', 'employer', 'vacancy'):
        c.status, c.ended_at = 'finished', timezone.now()
        c.save(update_fields=['status', 'ended_at', 'updated_at'])
        _free_worker(c.worker)
        finished += 1
        for person in (c.employer, c.worker.user):
            _notify(person, ('Contract finished', f'The contract for "{c.vacancy.title}" has finished. Please rate it.'),
                    'job_completed', contract=c)
    soon = today + timedelta(days=REMIND_DAYS)
    for c in EmploymentContract.objects.filter(status='active', ending_reminder_sent=False,
                                               end_date__gte=today, end_date__lte=soon).select_related('worker__user', 'employer', 'vacancy'):
        for person in (c.employer, c.worker.user):
            _notify(person, ('Contract ending soon', f'The contract for "{c.vacancy.title}" ends on {c.end_date:%d %b %Y}.'),
                    'system_alert', contract=c)
        c.ending_reminder_sent = True
        c.save(update_fields=['ending_reminder_sent', 'updated_at'])
        reminded += 1
    return {'closed': closed, 'finished': finished, 'reminded': reminded}


# --------------------------------------------------------------------- notifications

def _notify(recipient, title_message, ntype, vacancy=None, application=None, contract=None, send_email=True):
    from worker_connect.notification_service import NotificationService
    title, message = title_message
    extra = {}
    if vacancy is not None:
        extra['vacancy_id'] = vacancy.pk
    if application is not None:
        extra['application_id'] = application.pk
    if contract is not None:
        extra['contract_id'] = contract.pk
        extra.setdefault('vacancy_id', contract.vacancy_id)
    try:
        return NotificationService.create_notification(
            recipient=recipient, title=title, message=message, notification_type=ntype,
            content_object=contract or application or vacancy, extra_data=extra, send_email=send_email)
    except Exception:
        logger.exception('job post notification failed (%s)', title)
        return None


def _notify_admins(title_message, extra=None):
    from accounts.models import User
    from worker_connect.notification_service import NotificationService
    title, message = title_message
    for admin in User.objects.filter(Q(is_staff=True) | Q(user_type='admin'), is_active=True):
        try:
            NotificationService.create_notification(recipient=admin, title=title, message=message,
                                                    notification_type='system_alert', extra_data=extra or {})
        except Exception:
            logger.exception('admin notification failed (%s)', title)


def _notify_admins_to_review(vacancy):
    _notify_admins(('Job post to review', f'{vacancy.poster_display_name}: "{vacancy.title}" in {vacancy.city}'),
                   extra={'vacancy_id': vacancy.pk})
