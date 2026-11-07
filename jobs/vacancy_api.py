"""
App API for job posts. Every action goes through jobs/vacancy_service.py, the
same rules the website uses. Output is built per viewer: the exact address and
phone numbers only reach the people allowed to see them.

    GET  /api/vacancies/                      published jobs (workers)
    POST /api/vacancies/                      post a job (clients)
    GET  /api/vacancies/mine/                 my job posts (poster)
    GET  /api/vacancies/<id>/                 one job
    PATCH /api/vacancies/<id>/                edit + resubmit (poster)
    POST /api/vacancies/<id>/close/
    POST /api/vacancies/<id>/apply/
    POST /api/vacancies/<id>/report/
    GET  /api/vacancies/<id>/applications/    applicants (poster / admin)
    POST /api/vacancies/applications/<id>/<shortlist|reject|hire|withdraw>/
    GET  /api/vacancies/my-applications/      (worker)
    GET  /api/vacancies/contracts/            (worker / employer)
    GET  /api/vacancies/contracts/<id>/
    POST /api/vacancies/contracts/<id>/<end|renew|rate|report>/
    GET  /api/vacancies/review/               queue (admin)
    POST /api/vacancies/<id>/review/          publish / changes / reject (admin)
    GET  /api/vacancies/options/              choices for the post form
"""
from django.db.models import Count, Q  # noqa: F401
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from worker_connect.pagination import StandardResultsSetPagination
from workers.models import Category

from . import vacancy_service as svc
from .chat_access import is_admin
from .vacancy_forms import HireForm, VacancyForm
from .vacancy_models import EmploymentContract, Vacancy, VacancyApplication


def _err(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': message}, status=code)


def _form_errors(form):
    errors = {k: [str(e) for e in v] for k, v in form.errors.items()}
    first = next(iter(errors.values()), ['Please check the form.'])[0]
    return Response({'error': first, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)


def _money(v):
    return str(v) if v is not None else None


# ------------------------------------------------------------------ output

def vacancy_data(user, v, full=True):
    data = {
        'id': v.id,
        'title': v.title,
        'kind': v.kind,
        'kind_display': v.get_kind_display(),
        'poster_name': v.poster_display_name,
        'category': v.category_id,
        'category_name': v.category.name if v.category_id else '',
        'workers_needed': v.workers_needed,
        'places_left': v.places_left,
        'duration': v.duration,
        'duration_display': v.get_duration_display(),
        'start_date': v.start_date.isoformat(),
        'closing_date': v.closing_date.isoformat(),
        'salary_amount': _money(v.salary_amount),
        'salary_max': _money(v.salary_max),
        'pay_period': v.pay_period,
        'pay_period_display': v.get_pay_period_display(),
        'city': v.city,
        'area': v.area,
        'worker_type_needed': v.worker_type_needed,
        'worker_type_display': v.get_worker_type_needed_display(),
        'live_in': v.live_in,
        'food_provided': v.food_provided,
        'room_provided': v.room_provided,
        'status': v.status,
        'status_display': v.get_status_display(),
        'is_open': v.is_open,
        'published_at': v.published_at.isoformat() if v.published_at else None,
        'created_at': v.created_at.isoformat(),
    }
    if not full:
        return data
    data.update({
        'description': v.description,
        'requirements': v.requirements,
        'pay_day': v.pay_day,
        'working_days': v.working_days,
        'working_hours': v.working_hours,
        'duties': v.duties,
        'trial_period': v.trial_period,
        'can_manage': svc.can_manage(user, v),
        'hired_count': v.hired_count,
    })
    if svc.sees_private_details(user, v):
        data['address'] = v.address
        data['poster_phone'] = v.poster.phone_number or ''
    if svc.can_manage(user, v):
        data['review_note'] = v.review_note
        data['company_name'] = v.company_name
        data['verification_number'] = v.verification_number
        data['applicant_count'] = v.applicant_count
    profile = svc.worker_profile(user)
    if profile is not None:
        mine = v.applications.filter(worker=profile).first()
        data['my_application'] = application_data(user, mine, with_vacancy=False) if mine else None
        data['apply_problem'] = svc.apply_problem(user, v)
    return data


def application_data(user, a, with_vacancy=True):
    w = a.worker
    data = {
        'id': a.id,
        'status': a.status,
        'status_display': a.get_status_display(),
        'message': a.message,
        'created_at': a.created_at.isoformat(),
        'worker': {
            'id': w.id,
            'user_id': w.user_id,
            'name': w.user.get_full_name() or w.user.username,
            'worker_type': w.worker_type,
            'verified': w.verification_status == 'verified',
            'city': w.city,
            'experience_years': w.experience_years,
            'average_rating': _money(w.average_rating),
            'completed_jobs': w.completed_jobs,
            'categories': [c.name for c in w.categories.all()],
            'contracts_done': w.contracts_done if hasattr(w, 'contracts_done') else
            EmploymentContract.objects.filter(worker=w, status__in=('finished', 'renewed')).count(),
        },
    }
    if with_vacancy:
        data['vacancy'] = vacancy_data(user, a.vacancy, full=False)
    contracts = sorted(a.contracts.all(), key=lambda c: c.created_at, reverse=True)  # prefetched in lists
    data['contract_id'] = contracts[0].id if contracts else None
    return data


def _with_worker_history(apps):
    """contracts_done for every worker on the page in one query."""
    from collections import Counter
    workers = {a.worker_id for a in apps}
    done = Counter(EmploymentContract.objects.filter(worker_id__in=workers, status__in=('finished', 'renewed'))
                   .values_list('worker_id', flat=True))
    for a in apps:
        a.worker.contracts_done = done.get(a.worker_id, 0)
    svc.attach_counts([a.vacancy for a in apps])
    return apps


def contract_data(user, c):
    party = svc.contract_party(user, c)
    data = {
        'id': c.id,
        'my_role': party,
        'vacancy': vacancy_data(user, c.vacancy, full=False),
        'worker_name': c.worker.user.get_full_name() or c.worker.user.username,
        'worker_user_id': c.worker.user_id,
        'employer_name': c.vacancy.poster_display_name,
        'employer_user_id': c.employer_id,
        'start_date': c.start_date.isoformat(),
        'end_date': c.end_date.isoformat() if c.end_date else None,
        'salary_amount': _money(c.salary_amount),
        'pay_period': c.pay_period,
        'pay_period_display': c.get_pay_period_display(),
        'terms': c.terms,
        'status': c.status,
        'status_display': c.get_status_display(),
        'end_reason': c.end_reason,
        'employer_rating': c.employer_rating,
        'employer_feedback': c.employer_feedback,
        'worker_rating': c.worker_rating,
        'worker_feedback': c.worker_feedback,
        'renewed_to': c.renewed_to_id if hasattr(c, 'renewed_to_id') else
        getattr(getattr(c, 'renewal', None), 'id', None),
        'renewed_from': c.renewed_from_id,
    }
    # address and the other side's phone (Call button): only while this hire is
    # open - an early end closes it for every period, renewals included
    open_rel = svc.relationship_open(c)
    data['relationship_open'] = open_rel
    if party == 'admin' or open_rel:
        data['address'] = c.vacancy.address
    if open_rel:
        if party == 'employer':
            data['other_phone'] = c.worker.user.phone_number or ''
        elif party == 'worker':
            data['other_phone'] = c.employer.phone_number or ''
    return data


def _page(request, qs, fn, prepare=None):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    rows = list(page if page is not None else qs)
    if prepare:
        prepare(rows)
    items = [fn(x) for x in rows]
    return paginator.get_paginated_response(items) if page is not None else Response(items)


def _prepare_contracts(rows):
    renewal = dict(EmploymentContract.objects.filter(renewed_from__in=[c.pk for c in rows])
                   .values_list('renewed_from_id', 'id'))
    for c in rows:
        c.renewed_to_id = renewal.get(c.pk)
    svc.attach_counts([c.vacancy for c in rows])


# ------------------------------------------------------------------ jobs

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vacancies(request):
    if request.method == 'POST':
        if not svc.can_post(request.user):
            return _err('Only clients can post jobs.', status.HTTP_403_FORBIDDEN)
        form = VacancyForm(data=request.data)
        if not form.is_valid():
            return _form_errors(form)
        v = svc.submit(request.user, form)
        return Response(vacancy_data(request.user, v), status=status.HTTP_201_CREATED)
    if svc.worker_profile(request.user) is None and not is_admin(request.user):
        return _err('The job list is for workers.', status.HTTP_403_FORBIDDEN)
    qs = svc.jobs_for_worker(request.user, request.GET)
    return _page(request, qs, lambda v: vacancy_data(request.user, v, full=False))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def options(request):
    return Response({
        'categories': [{'id': c.id, 'name': c.name} for c in Category.objects.filter(is_active=True).order_by('name')],
        'kinds': [{'value': k, 'label': l} for k, l in Vacancy.KIND_CHOICES],
        'durations': [{'value': k, 'label': l} for k, l in Vacancy.DURATION_CHOICES],
        'pay_periods': [{'value': k, 'label': l} for k, l in Vacancy.PAY_PERIOD_CHOICES],
        'worker_types': [{'value': k, 'label': l} for k, l in Vacancy.WORKER_TYPE_CHOICES],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mine(request):
    qs = svc.with_counts(Vacancy.objects.filter(poster=request.user).select_related('category', 'poster'))
    return _page(request, qs, lambda v: vacancy_data(request.user, v))


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def vacancy_detail(request, pk):
    v = get_object_or_404(Vacancy.objects.select_related('category', 'poster'), pk=pk)
    if not svc.can_view(request.user, v):
        return _err('Job not found.', status.HTTP_404_NOT_FOUND)
    if request.method == 'PATCH':
        # start from what is saved, then apply the fields the app sent
        data = model_to_dict(v, fields=VacancyForm.Meta.fields)
        incoming = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        data.update({k: val for k, val in incoming.items() if k in VacancyForm.Meta.fields})
        form = VacancyForm(data=data, instance=v)
        if not form.is_valid():
            return _form_errors(form)
        try:
            v = svc.resubmit(request.user, v, form)
        except svc.VacancyError as e:
            return _err(str(e), status.HTTP_403_FORBIDDEN)
    return Response(vacancy_data(request.user, v))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    if not svc.can_view(request.user, v):
        return _err('Job not found.', status.HTTP_404_NOT_FOUND)
    try:
        v = svc.close(request.user, v)
    except svc.VacancyError as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST if svc.can_manage(request.user, v) else status.HTTP_403_FORBIDDEN)
    return Response(vacancy_data(request.user, v))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    if not svc.can_view(request.user, v):
        return _err('Job not found.', status.HTTP_404_NOT_FOUND)
    try:
        a = svc.apply(request.user, v, str(request.data.get('message', ''))[:2000])
    except svc.VacancyError as e:
        return _err(str(e))
    return Response(application_data(request.user, a), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_vacancy(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    return _report(request, v)


def _report(request, obj):
    from .models import Report
    rtype = request.data.get('report_type') or 'other'
    if rtype not in dict(Report.REPORT_TYPE_CHOICES):
        return _err('Choose what is wrong.')
    desc = str(request.data.get('description', '')).strip()
    if not desc:
        return _err('Please tell us what happened.')
    try:
        svc.report(request.user, obj, rtype, desc[:2000])
    except svc.VacancyError as e:
        return _err(str(e), status.HTTP_404_NOT_FOUND)
    return Response({'message': 'Thank you. Our team will look at it.'}, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------ applicants

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def applications(request, pk):
    v = get_object_or_404(Vacancy, pk=pk)
    if not svc.can_manage(request.user, v):
        return _err('Job not found.', status.HTTP_404_NOT_FOUND)
    qs = (v.applications.exclude(status='withdrawn')
          .select_related('worker__user', 'vacancy').prefetch_related('worker__categories', 'contracts'))
    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return _page(request, qs, lambda a: application_data(request.user, a, with_vacancy=False),
                 prepare=_with_worker_history)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def application_action(request, pk, action):
    a = get_object_or_404(VacancyApplication.objects.select_related('vacancy', 'worker__user'), pk=pk)
    owner = svc.worker_profile(request.user) is not None and a.worker.user_id == request.user.id
    if not (owner or svc.can_manage(request.user, a.vacancy)):
        return _err('Application not found.', status.HTTP_404_NOT_FOUND)
    try:
        if action == 'withdraw':
            svc.withdraw(request.user, a)
        elif action == 'shortlist':
            svc.shortlist(request.user, a)
        elif action == 'reject':
            svc.turn_down(request.user, a)
        elif action == 'hire':
            form = HireForm(data=request.data)
            if not form.is_valid():
                return _form_errors(form)
            contract = svc.hire(request.user, a, form.cleaned_data.get('start_date'),
                                form.cleaned_data.get('terms', ''))
            return Response(contract_data(request.user, contract), status=status.HTTP_201_CREATED)
        else:
            return _err('Unknown action.', status.HTTP_404_NOT_FOUND)
    except svc.VacancyError as e:
        return _err(str(e))
    a.refresh_from_db()
    return Response(application_data(request.user, a))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_applications(request):
    profile = svc.worker_profile(request.user)
    if profile is None:
        return _err('Only workers have applications.', status.HTTP_403_FORBIDDEN)
    qs = (VacancyApplication.objects.filter(worker=profile)
          .select_related('vacancy__category', 'vacancy__poster', 'worker__user')
          .prefetch_related('worker__categories', 'contracts'))
    return _page(request, qs, lambda a: application_data(request.user, a), prepare=_with_worker_history)


# ------------------------------------------------------------------ contracts

def _my_contracts(user):
    qs = EmploymentContract.objects.select_related('vacancy__category', 'vacancy__poster', 'worker__user', 'employer')
    if is_admin(user):
        return qs
    profile = svc.worker_profile(user)
    if profile is not None:
        return qs.filter(worker=profile)
    return qs.filter(employer=user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contracts(request):
    qs = _my_contracts(request.user).select_related('application')
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    return _page(request, qs, lambda c: contract_data(request.user, c), prepare=_prepare_contracts)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contract_detail(request, pk):
    c = get_object_or_404(_my_contracts(request.user), pk=pk)
    return Response(contract_data(request.user, c))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def contract_action(request, pk, action):
    c = get_object_or_404(_my_contracts(request.user), pk=pk)
    if action == 'report':
        return _report(request, c)
    try:
        if action == 'end':
            c = svc.end_contract(request.user, c, str(request.data.get('reason', ''))[:2000])
        elif action == 'renew':
            c = svc.renew(request.user, c, request.data.get('duration', ''))
        elif action == 'rate':
            try:
                rating = int(request.data.get('rating', 0))
            except (TypeError, ValueError):
                return _err('Choose 1 to 5 stars.')
            c = svc.rate(request.user, c, rating, str(request.data.get('feedback', ''))[:2000])
        else:
            return _err('Unknown action.', status.HTTP_404_NOT_FOUND)
    except svc.VacancyError as e:
        return _err(str(e))
    return Response(contract_data(request.user, c))


# ------------------------------------------------------------------ admin

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def review_queue(request):
    if not is_admin(request.user):
        return _err('Admins only.', status.HTTP_403_FORBIDDEN)
    qs = svc.with_counts(Vacancy.objects.filter(status__in=('review', 'changes')).select_related('category', 'poster'))
    return _page(request, qs.order_by('created_at'), lambda v: vacancy_data(request.user, v))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review(request, pk):
    if not is_admin(request.user):
        return _err('Admins only.', status.HTTP_403_FORBIDDEN)
    from .vacancy_forms import ReviewForm
    v = get_object_or_404(Vacancy, pk=pk)
    form = ReviewForm(data=request.data)
    if not form.is_valid():
        return _form_errors(form)
    try:
        v = svc.review(request.user, v, form.cleaned_data['action'], form.cleaned_data.get('note', ''))
    except svc.VacancyError as e:
        return _err(str(e))
    return Response(vacancy_data(request.user, v))
