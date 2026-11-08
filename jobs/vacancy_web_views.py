"""
Website pages for job posts. Same rules as the app (jobs/vacancy_service.py).

Clients:  post a job, my job posts, one job with its applicants, contracts
Workers:  job board, one job (apply / withdraw), my applications, contracts
Admins:   review queue, all job posts, any job / contract
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from workers.models import Category

from . import vacancy_service as svc
from .chat_access import is_admin
from .vacancy_forms import (ApplyForm, EndContractForm, HireForm, RateForm, RenewForm, ReportForm,
                            ReviewForm, VacancyForm)
from .vacancy_models import EmploymentContract, Vacancy, VacancyApplication
from .views import _chat_base_template


def _ctx(request, **extra):
    return {'base_template': _chat_base_template(request.user), 'me_admin': is_admin(request.user), **extra}


def _page(request, qs, per=20):
    return Paginator(qs, per).get_page(request.GET.get('page'))


# ------------------------------------------------------------------ worker board

@login_required
def board(request):
    """Published jobs. Workers apply here; clients are sent to their own posts."""
    if svc.worker_profile(request.user) is None and not is_admin(request.user):
        return redirect('vacancies:mine')
    params = request.GET
    jobs = svc.jobs_for_worker(request.user, params)  # already annotated with counts
    return render(request, 'vacancies/board.html', _ctx(
        request, jobs=_page(request, jobs), params=params,
        categories=Category.objects.filter(is_active=True).order_by('name'),
        durations=Vacancy.DURATION_CHOICES, profile=svc.worker_profile(request.user)))


@login_required
def my_applications(request):
    profile = svc.worker_profile(request.user)
    if profile is None:
        raise Http404
    apps = (VacancyApplication.objects.filter(worker=profile)
            .select_related('vacancy__category', 'vacancy__poster').prefetch_related('contracts'))
    return render(request, 'vacancies/my_applications.html', _ctx(request, applications=_page(request, apps)))


# ------------------------------------------------------------------ poster

@login_required
def post(request, pk=None):
    """New job post, or edit one that is under review / sent back / rejected."""
    vacancy = None
    if pk:
        vacancy = get_object_or_404(Vacancy, pk=pk, poster=request.user)
        if vacancy.status not in ('review', 'changes', 'rejected'):
            messages.warning(request, _('A published job cannot be edited. Close it and post a new one.'))
            return redirect('vacancies:detail', pk=pk)
    elif not svc.can_post(request.user):
        messages.error(request, _('Only clients can post jobs.'))
        return redirect('home')
    initial = {}
    if vacancy is None and hasattr(request.user, 'client_profile'):
        cp = request.user.client_profile
        initial = {'company_name': cp.company_name, 'city': cp.city,
                   'kind': 'business' if cp.company_name else 'home'}
    if request.GET.get('kind') in ('home', 'business'):
        initial['kind'] = request.GET['kind']
    form = VacancyForm(request.POST or None, instance=vacancy, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            vacancy = svc.resubmit(request.user, vacancy, form) if vacancy else svc.submit(request.user, form)
        except svc.VacancyError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, _('Thank you! Your job post is under review. We will tell you when it is published.'))
            return redirect('vacancies:detail', pk=vacancy.pk)
    return render(request, 'vacancies/post.html', _ctx(request, form=form, vacancy=vacancy))


@login_required
def mine(request):
    if is_admin(request.user):
        return redirect('vacancies:admin_all')
    posts = svc.with_counts(Vacancy.objects.filter(poster=request.user).select_related('category', 'poster'))
    return render(request, 'vacancies/mine.html', _ctx(request, posts=_page(request, posts)))


# ------------------------------------------------------------------ one job

@login_required
def detail(request, pk):
    v = get_object_or_404(Vacancy.objects.select_related('category', 'poster', 'reviewed_by'), pk=pk)
    if not svc.can_view(request.user, v):
        raise Http404
    manage = svc.can_manage(request.user, v)
    profile = svc.worker_profile(request.user)
    ctx = _ctx(request, v=v, manage=manage, private=svc.sees_private_details(request.user, v),
               report_form=ReportForm())
    if manage:
        status_filter = request.GET.get('status', '')
        apps = (v.applications.exclude(status='withdrawn')
                .select_related('worker__user').prefetch_related('worker__categories', 'contracts')
                .annotate(worker_contracts=Count('worker__contracts', distinct=True)))
        if status_filter:
            apps = apps.filter(status=status_filter)
        ctx.update(applications=apps, status_filter=status_filter, hire_form=HireForm(),
                   review_form=ReviewForm(), contracts=v.contracts.select_related('worker__user'),
                   counts={s: v.applications.filter(status=s).count() for s, _l in VacancyApplication.STATUS_CHOICES})
    if profile is not None:
        ctx.update(my_application=v.applications.filter(worker=profile).first(),
                   apply_problem=svc.apply_problem(request.user, v), apply_form=ApplyForm())
    return render(request, 'vacancies/detail.html', ctx)


def _run(request, fn, ok_message):
    try:
        result = fn()
    except svc.VacancyError as e:
        messages.error(request, str(e))
        return None
    messages.success(request, ok_message)
    return result


@login_required
@require_POST
def apply(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    if not svc.can_view(request.user, v):
        raise Http404
    form = ApplyForm(request.POST)
    message = form.cleaned_data['message'] if form.is_valid() else ''
    _run(request, lambda: svc.apply(request.user, v, message),
         _('Your application was sent. You will get a notification when the employer decides.'))
    return redirect('vacancies:detail', pk=pk)


@login_required
@require_POST
def close(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    if not svc.can_view(request.user, v):
        raise Http404
    _run(request, lambda: svc.close(request.user, v), _('The job is closed.'))
    return redirect('vacancies:detail', pk=pk)


@login_required
@require_POST
def review(request, pk):
    if not is_admin(request.user):
        raise Http404
    v = get_object_or_404(Vacancy, pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, _('Tell the poster why.') if 'note' in form.errors else _('Choose an action.'))
        return redirect('vacancies:detail', pk=pk)
    action = form.cleaned_data['action']
    done = {'publish': _('Published. Matching workers were notified.'),
            'changes': _('Sent back to the poster for changes.'),
            'reject': _('The job post was rejected.')}[action]
    if _run(request, lambda: svc.review(request.user, v, action, form.cleaned_data.get('note', '')), done):
        return redirect('vacancies:review_queue')
    return redirect('vacancies:detail', pk=pk)


@login_required
@require_POST
def report(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    return _report(request, v, redirect('vacancies:detail', pk=pk))


def _report(request, obj, back):
    form = ReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, _('Please tell us what happened.'))
        return back
    try:
        svc.report(request.user, obj, form.cleaned_data['report_type'], form.cleaned_data['description'])
    except svc.VacancyError:
        raise Http404
    messages.success(request, _('Thank you. Our team will look at it.'))
    return back


# ------------------------------------------------------------------ applicants

@login_required
@require_POST
def application_action(request, pk, action):
    a = get_object_or_404(VacancyApplication.objects.select_related('vacancy', 'worker__user'), pk=pk)
    owner = svc.worker_profile(request.user) is not None and a.worker.user_id == request.user.id
    if not (owner or svc.can_manage(request.user, a.vacancy)):
        raise Http404
    back = redirect('vacancies:detail', pk=a.vacancy_id)
    if action == 'withdraw':
        _run(request, lambda: svc.withdraw(request.user, a), _('Your application was withdrawn.'))
    elif action == 'shortlist':
        _run(request, lambda: svc.shortlist(request.user, a), _('Added to the shortlist.'))
    elif action == 'reject':
        _run(request, lambda: svc.turn_down(request.user, a), _('The applicant was told they were not selected.'))
    elif action == 'hire':
        form = HireForm(request.POST)
        if not form.is_valid():
            messages.error(request, _('Please check the start date.'))
            return back
        contract = _run(request, lambda: svc.hire(request.user, a, form.cleaned_data.get('start_date'),
                                                  form.cleaned_data.get('terms', '')),
                        _('Hired! You can now chat and call each other.'))
        if contract:
            return redirect('vacancies:contract', pk=contract.pk)
    else:
        raise Http404
    return back


# ------------------------------------------------------------------ contracts

def _my_contracts(user):
    qs = EmploymentContract.objects.select_related('vacancy__category', 'vacancy__poster', 'worker__user', 'employer')
    if is_admin(user):
        return qs
    profile = svc.worker_profile(user)
    return qs.filter(worker=profile) if profile is not None else qs.filter(employer=user)


@login_required
def contracts(request):
    qs = _my_contracts(request.user)
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'vacancies/contracts.html', _ctx(
        request, contracts=_page(request, qs), status_filter=status_filter,
        statuses=EmploymentContract.STATUS_CHOICES))


@login_required
def contract(request, pk):
    c = get_object_or_404(_my_contracts(request.user), pk=pk)
    party = svc.contract_party(request.user, c)
    my_rating = c.employer_rating if party == 'employer' else c.worker_rating if party == 'worker' else None
    other_user = c.worker.user if party == 'employer' else c.employer if party == 'worker' else None
    return render(request, 'vacancies/contract.html', _ctx(
        request, c=c, party=party, my_rating=my_rating, other_user=other_user,
        open_rel=svc.relationship_open(c),
        end_form=EndContractForm(), renew_form=RenewForm(), rate_form=RateForm(), report_form=ReportForm(),
        history=_contract_chain(c)))


def _contract_chain(c):
    """This contract and the ones it renewed, oldest first."""
    chain, cur = [], c
    while cur is not None:
        chain.append(cur)
        cur = cur.renewed_from
    later = getattr(c, 'renewal', None)
    while later is not None:
        chain.insert(0, later)
        later = getattr(later, 'renewal', None)
    return sorted(chain, key=lambda x: x.start_date)


@login_required
@require_POST
def contract_action(request, pk, action):
    c = get_object_or_404(_my_contracts(request.user), pk=pk)
    back = redirect('vacancies:contract', pk=pk)
    if action == 'end':
        form = EndContractForm(request.POST)
        if form.is_valid():
            _run(request, lambda: svc.end_contract(request.user, c, form.cleaned_data['reason']), _('The contract has ended.'))
        else:
            messages.error(request, _('Please give a reason.'))
    elif action == 'renew':
        form = RenewForm(request.POST)
        if form.is_valid():
            new = _run(request, lambda: svc.renew(request.user, c, form.cleaned_data['duration']), _('The contract was renewed.'))
            if new:
                return redirect('vacancies:contract', pk=new.pk)
        else:
            messages.error(request, _('Choose how long to renew for.'))
    elif action == 'rate':
        form = RateForm(request.POST)
        if form.is_valid():
            _run(request, lambda: svc.rate(request.user, c, form.cleaned_data['rating'], form.cleaned_data['feedback']),
                 _('Thank you for your rating.'))
        else:
            messages.error(request, _('Choose 1 to 5 stars.'))
    elif action == 'report':
        return _report(request, c, back)
    else:
        raise Http404
    return back


# ------------------------------------------------------------------ admin

@login_required
def review_queue(request):
    if not is_admin(request.user):
        raise Http404
    posts = svc.with_counts(Vacancy.objects.filter(status__in=('review', 'changes'))
                            .select_related('category', 'poster').order_by('created_at'))
    return render(request, 'vacancies/admin_list.html', _ctx(
        request, posts=_page(request, posts), queue=True, statuses=Vacancy.STATUS_CHOICES, status_filter=''))


@login_required
def admin_all(request):
    if not is_admin(request.user):
        raise Http404
    posts = svc.with_counts(Vacancy.objects.select_related('category', 'poster'))
    status_filter = request.GET.get('status', '')
    if status_filter:
        posts = posts.filter(status=status_filter)
    if request.GET.get('q'):
        q = request.GET['q']
        from django.db.models import Q
        posts = posts.filter(Q(title__icontains=q) | Q(company_name__icontains=q) | Q(city__icontains=q)
                             | Q(poster__first_name__icontains=q) | Q(poster__last_name__icontains=q))
    return render(request, 'vacancies/admin_list.html', _ctx(
        request, posts=_page(request, posts), queue=False, statuses=Vacancy.STATUS_CHOICES,
        status_filter=status_filter))
