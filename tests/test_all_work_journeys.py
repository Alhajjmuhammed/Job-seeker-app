"""
Whole journeys for every way of getting work, start to finish, as real website
and app requests - and the places where the different kinds of work meet.

  1. Quick service by category (booking -> payment -> assign -> work -> finish)
  2. Long-term home job (house girl, 3 / 6 months): post -> review -> apply -> hire -> contract
  3. Company job post (same system, "business")
  4. Direct hire (client books one worker)

    python manage.py test tests.test_all_work_journeys
"""
from datetime import timedelta
from decimal import Decimal as D

from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone

from jobs.chat_access import can_chat
from jobs.models import DirectHireRequest
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from jobs.vacancy_models import EmploymentContract, Vacancy, VacancyApplication
from jobs.vacancy_service import daily_maintenance
from workers.models import WorkerDocument

from .test_full_flows import PNG, post_json
from .test_vacancies import API, VacancyBase


class Journeys(VacancyBase):
    def setUp(self):
        super().setUp()
        self.w2_c = Client()
        self.w2_c.force_login(self.worker2_user)

    def refresh(self, *objs):
        for o in objs:
            o.refresh_from_db()

    # ------------------------------------------------------------ 1. quick service
    def test_1_quick_service_two_workers_one_refuses_replacement_finishes(self):
        sr, _ = self.book(workers=2)
        self.assertEqual(sr.status, 'pending')
        # client sees it, a stranger does not
        self.assertEqual(self.client_c.get(f'/services/client/request/{sr.id}/').status_code, 200)
        other = Client(); other.force_login(self.other_client)
        self.assertNotEqual(other.get(f'/services/client/request/{sr.id}/').status_code, 200)

        # admin assigns worker 1 (website) and worker 2 (app API)
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp2.id})
        a1 = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        a2 = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp2)
        self.refresh(sr)
        self.assertEqual(sr.status, 'assigned')
        self.assertFalse(can_chat(self.client_user, self.worker_user))  # no chat before accepting

        # worker 1 accepts, worker 2 refuses
        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{a1.id}/respond/', {'accepted': True})
        self.assertEqual(r.status_code, 200, r.content)
        r = post_json(self.w2_c, f'/api/v1/worker/my-assignments/{a2.id}/respond/',
                      {'accepted': False, 'rejection_reason': 'sick'})
        self.assertEqual(r.status_code, 200, r.content)
        self.refresh(sr, a1, a2, self.wp, self.wp2)
        self.assertEqual((a1.status, a2.status), ('accepted', 'rejected'))
        self.assertEqual(sr.status, 'in_progress')
        self.assertEqual(self.wp.availability, 'busy')
        self.assertEqual(self.wp2.availability, 'available')
        self.assertTrue(can_chat(self.client_user, self.worker_user))
        # the client can no longer cancel a started job (app or website)
        self.assertEqual(post_json(self.client_c, f'/api/v1/client/service-requests/{sr.id}/cancel/').status_code, 400)

        # worker 1 works and finishes
        self.assertEqual(post_json(self.worker_c, f'/api/v1/worker/my-assignments/{a1.id}/clock-in/').status_code, 200)
        self.assertEqual(post_json(self.worker_c, f'/api/v1/worker/my-assignments/{a1.id}/clock-out/').status_code, 200)
        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{a1.id}/complete/', {'completion_notes': 'done'})
        self.assertEqual(r.status_code, 200, r.content)
        self.refresh(sr, a1, self.wp)
        self.assertEqual(a1.status, 'completed')
        self.assertNotEqual(sr.status, 'completed')  # paid for 2, 1 finished: admin decides
        self.assertEqual(sr.short_staffed(), (1, 2))
        earned_once = self.wp.total_earnings

        # admin assigns a replacement; they accept and finish -> the job closes by itself
        self.wp2.availability = 'available'
        self.wp2.save(update_fields=['availability'])
        from workers.models import WorkerProfile
        from accounts.models import User
        u3 = User.objects.create_user(email='w3@t.co', username='workthree', password='x-Pass-2026!',
                                      user_type='worker', first_name='Three')
        wp3 = WorkerProfile.objects.create(user=u3, verification_status='verified', availability='available', city='Dar')
        wp3.categories.add(self.cat)
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': wp3.id})
        self.assertIn(r.status_code, (200, 201), r.content)
        self.refresh(sr)
        self.assertEqual(sr.status, 'in_progress')  # not dragged back to "assigned"
        a3 = ServiceRequestAssignment.objects.get(service_request=sr, worker=wp3)
        c3 = Client(); c3.force_login(u3)
        self.assertEqual(post_json(c3, f'/api/v1/worker/my-assignments/{a3.id}/respond/', {'accepted': True}).status_code, 200)
        self.assertEqual(post_json(c3, f'/api/v1/worker/my-assignments/{a3.id}/complete/', {}).status_code, 200)
        self.refresh(sr, self.wp)
        self.assertEqual(sr.status, 'completed')
        self.assertIsNotNone(sr.work_completed_at)
        self.assertEqual(self.wp.total_earnings, earned_once)  # nobody paid twice
        self.assertEqual(self.wp.availability, 'available')

        # client rates; pages still open for everyone involved
        self.assertLess(self.client_c.get(f'/services/client/request/{sr.id}/').status_code, 400)
        self.assertEqual(self.admin_c.get(f'/dashboard/service-requests/{sr.id}/').status_code, 200)
        self.assertEqual(self.worker_c.get(f'/services/worker/assignment/{a1.id}/').status_code, 200)

    def test_1b_quick_service_cancel_before_start_frees_everyone(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        r = post_json(self.client_c, f'/api/v1/client/service-requests/{sr.id}/cancel/')
        self.assertEqual(r.status_code, 200, r.content)
        self.refresh(sr, self.wp)
        self.assertEqual(sr.status, 'cancelled')
        self.assertEqual(self.wp.availability, 'available')
        a = ServiceRequestAssignment.objects.get(service_request=sr)
        self.assertEqual(a.status, 'cancelled')
        # the worker can't act on it any more, and admin can't bring it back
        self.assertGreaterEqual(post_json(self.worker_c, f'/api/v1/worker/my-assignments/{a.id}/respond/', {'accepted': True}).status_code, 400)
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/assign/', {'worker_id': self.wp2.id})
        self.refresh(sr)
        self.assertEqual(sr.status, 'cancelled')

    def test_1c_quick_service_website_end_to_end(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        a = ServiceRequestAssignment.objects.get(service_request=sr)
        self.worker_c.post(f'/services/worker/assignment/{a.id}/respond/', {'action': 'accept'})
        self.refresh(a)
        if a.status == 'pending':  # field name used by the website form
            self.worker_c.post(f'/services/worker/assignment/{a.id}/respond/', {'response': 'accept'})
            self.refresh(a)
        self.assertEqual(a.status, 'accepted')
        self.worker_c.post(f'/services/worker/assignment/{a.id}/clock-in/')
        self.worker_c.post(f'/services/worker/assignment/{a.id}/clock-out/')
        self.client_c.post(f'/services/client/request/{sr.id}/complete/')
        self.refresh(sr, a)
        self.assertEqual(sr.status, 'completed')
        self.assertEqual(a.status, 'completed')
        self.assertIsNotNone(sr.work_completed_at)

    # ------------------------------------------------------------ 2. house girl, 3 months
    def test_2_house_girl_three_months_full_contract(self):
        v = self.post_job(kind='home', duration='3_months', live_in=True)
        self.assertEqual(v.status, 'review')
        self.assertEqual(self.worker_c.get(f'{API}{v.id}/').status_code, 404)  # hidden before review
        self.publish(v)
        d = self.worker_c.get(f'{API}{v.id}/').json()
        self.assertNotIn('address', d)  # no address before hire
        self.apply(v)
        self.apply(v, c=self.w2_c)
        apps = {a.worker_id: a for a in VacancyApplication.objects.filter(vacancy=v)}
        self.hire(apps[self.wp.id])
        self.refresh(v, self.wp)
        c = EmploymentContract.objects.get(vacancy=v)
        self.assertEqual((c.end_date - c.start_date).days, 91)  # 3 months
        self.assertEqual(v.status, 'filled')
        self.assertEqual(self.wp.availability, 'busy')
        self.assertEqual(VacancyApplication.objects.get(pk=apps[self.wp2.id].pk).status, 'not_selected')
        self.assertTrue(can_chat(self.client_user, self.worker_user))
        self.assertEqual(self.worker_c.get(f'{API}{v.id}/').json().get('address'), 'Plot 7, Secret Lane')

        # a house girl on a contract is not sent to quick-service jobs
        sr, _ = self.book()
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        self.assertEqual(r.status_code, 400, r.content)

        # contract runs out (in Tanzania time) -> finished, worker free; chat stays open after a
        # normal finish (by design, for follow-up) - it closes only when ended early
        daily_maintenance(today=c.end_date + timedelta(days=1))
        self.refresh(c, self.wp)
        self.assertEqual(c.status, 'finished')
        self.assertEqual(self.wp.availability, 'available')
        self.assertTrue(can_chat(self.client_user, self.worker_user))
        r = post_json(self.client_c, f'{API}contracts/{c.id}/rate/', {'rating': 5, 'review': 'Very good'})
        self.assertEqual(r.status_code, 200, r.content)

    def test_2b_six_month_contract_renewed_then_ended_early(self):
        v = self.publish(self.post_job(kind='home', duration='6_months'))
        self.apply(v)
        self.hire(VacancyApplication.objects.get(vacancy=v))
        c = EmploymentContract.objects.get(vacancy=v)
        self.assertEqual((c.end_date - c.start_date).days, 182)
        r = post_json(self.client_c, f'{API}contracts/{c.id}/renew/', {'duration': '3_months'})
        self.assertIn(r.status_code, (200, 201), r.content)
        new = EmploymentContract.objects.filter(worker=self.wp, status='active').latest('id')
        r = post_json(self.worker_c, f'{API}contracts/{new.id}/end/', {'reason': 'going home'})
        self.assertEqual(r.status_code, 200, r.content)
        self.refresh(self.wp)
        self.assertEqual(self.wp.availability, 'available')
        self.assertFalse(can_chat(self.client_user, self.worker_user))

    # ------------------------------------------------------------ 3. company job
    def test_3_company_job_professional_only(self):
        self.wp2.worker_type = 'professional'
        self.wp2.save(update_fields=['worker_type'])
        v = self.publish(self.post_job(kind='business', company_name='Mbezi Traders Ltd',
                                       worker_type_needed='professional', title='Accountant',
                                       duration='12_months', pay_period='month'))
        self.assertEqual(v.kind, 'business')
        self.apply(v, expect=400)  # non-academic worker can't apply to a professional job
        self.apply(v, c=self.w2_c)
        board = self.w2_c.get(f'{API}?kind=business').json()
        ids = [j['id'] for j in (board.get('results', board) if isinstance(board, dict) else board)]
        self.assertIn(v.id, ids)
        self.hire(VacancyApplication.objects.get(vacancy=v, worker=self.wp2))
        c = EmploymentContract.objects.get(vacancy=v)
        self.assertEqual((c.end_date - c.start_date).days, 365)
        for url in (f'/vacancies/{v.id}/', f'/vacancies/contracts/{c.id}/'):
            self.assertEqual(self.client_c.get(url).status_code, 200, url)
            self.assertEqual(self.w2_c.get(url).status_code, 200, url)

    # ------------------------------------------------------------ 4. direct hire
    def test_4_direct_hire_website_request_accept_complete(self):
        WorkerDocument.objects.create(worker=self.wp, document_type='id', title='ID', file='worker_documents/id.png',
                                      verification_status='approved')
        start = (timezone.localtime() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        r = self.client_c.post(f'/jobs/direct-hire/request/{self.wp.id}/', {
            'title': 'Paint my room', 'description': 'Two rooms', 'location': 'Mbezi',
            'duration_type': 'days', 'duration_value': 2, 'start_datetime': start, 'offered_rate': '30000'})
        self.assertEqual(r.status_code, 302, r.content[:400])
        hire = DirectHireRequest.objects.get(client=self.client_user)
        self.assertEqual(hire.total_amount, D('60000'))  # rate x 2 days, as the form shows
        self.assertEqual(self.worker_c.get(f'/jobs/direct-hire/{hire.id}/').status_code, 200)
        self.worker_c.post(f'/jobs/direct-hire/{hire.id}/accept/', {'response_message': 'ok'})
        self.refresh(hire, self.wp)
        self.assertEqual((hire.status, self.wp.availability), ('accepted', 'busy'))
        self.assertTrue(can_chat(self.client_user, self.worker_user))
        # the worker can't mark it complete, the client can
        self.worker_c.post(f'/jobs/direct-hire/{hire.id}/complete/', {'rating': 5})
        self.refresh(hire)
        self.assertEqual(hire.status, 'accepted')
        self.client_c.post(f'/jobs/direct-hire/{hire.id}/complete/', {'rating': 5, 'feedback': 'great'})
        self.refresh(hire, self.wp)
        self.assertEqual((hire.status, hire.client_rating), ('completed', 5))
        self.assertEqual(self.wp.availability, 'available')
        self.assertEqual(self.wp.total_earnings, D('60000'))

    def test_4b_direct_hire_declined_and_cancelled(self):
        def make(status='pending'):
            return DirectHireRequest.objects.create(
                client=self.client_user, worker=self.wp, title='x', description='x', location='x',
                duration_type='hours', duration_value=3, start_datetime=timezone.now() + timedelta(days=1),
                offered_rate=D('5000'), status=status)
        h = make()
        self.worker_c.post(f'/jobs/direct-hire/{h.id}/reject/', {'response_message': 'busy'})
        self.refresh(h)
        self.assertEqual(h.status, 'rejected')
        self.assertEqual(post_json(self.client_c, f'/api/jobs/direct-hire-requests/{h.id}/cancel/').status_code, 400)
        h2 = make()
        self.assertEqual(post_json(self.client_c, f'/api/jobs/direct-hire-requests/{h2.id}/cancel/').status_code, 200)
        self.refresh(h2)
        self.assertEqual(h2.status, 'cancelled')

    # ------------------------------------------------------------ where they meet
    def test_5_worker_free_only_when_every_kind_of_work_is_done(self):
        # on a house-girl contract AND a direct hire: finishing the direct hire keeps them busy
        v = self.publish(self.post_job())
        self.apply(v)
        self.hire(VacancyApplication.objects.get(vacancy=v))
        h = DirectHireRequest.objects.create(
            client=self.other_client, worker=self.wp, title='x', description='x', location='x',
            duration_type='hours', duration_value=2, start_datetime=timezone.now(), offered_rate=D('5000'),
            status='accepted')
        oc = Client(); oc.force_login(self.other_client)
        oc.post(f'/jobs/direct-hire/{h.id}/complete/', {'rating': 4})
        self.refresh(self.wp)
        self.assertEqual(self.wp.availability, 'busy')  # still on the contract
        c = EmploymentContract.objects.get(vacancy=v)
        post_json(self.client_c, f'{API}contracts/{c.id}/end/', {'reason': 'done'})
        self.refresh(self.wp)
        self.assertEqual(self.wp.availability, 'available')

    def test_6_no_second_long_contract_but_a_few_days_job_is_fine(self):
        v1 = self.publish(self.post_job(title='House girl 3 months'))
        v2 = self.publish(self.post_job(title='Another family, 6 months', duration='6_months'))
        v3 = self.publish(self.post_job(title='Party help', duration='one_off'))
        for v in (v1, v2, v3):
            self.apply(v)
        self.hire(VacancyApplication.objects.get(vacancy=v1))
        r = post_json(self.client_c, f'{API}applications/{VacancyApplication.objects.get(vacancy=v2).id}/hire/', {})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('already on a contract until', r.content.decode())
        self.hire(VacancyApplication.objects.get(vacancy=v3))  # "a few days" job still allowed

    def test_7_busy_worker_cannot_accept_a_direct_hire_but_can_decline(self):
        self.wp.availability = 'busy'
        self.wp.save(update_fields=['availability'])

        def make():
            return DirectHireRequest.objects.create(
                client=self.other_client, worker=self.wp, title='x', description='x', location='x',
                duration_type='hours', duration_value=2, start_datetime=timezone.now() + timedelta(days=1),
                offered_rate=D('5000'))
        h = make()
        self.worker_c.post(f'/jobs/direct-hire/{h.id}/accept/', {'response_message': 'ok'})
        h.refresh_from_db()
        self.assertEqual(h.status, 'pending')
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h.id}/accept/')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get('code'), 'worker_busy')
        page = self.worker_c.get(f'/jobs/direct-hire/{h.id}/').content.decode()
        self.assertIn('You are busy with other work', page)
        self.assertNotIn('Accept request', page)
        self.worker_c.post(f'/jobs/direct-hire/{h.id}/reject/', {'response_message': 'busy'})
        h.refresh_from_db()
        self.assertEqual(h.status, 'rejected')
        self.wp.availability = 'available'  # free again -> can accept
        self.wp.save(update_fields=['availability'])
        h2 = make()
        self.worker_c.post(f'/jobs/direct-hire/{h2.id}/accept/', {'response_message': 'ok'})
        h2.refresh_from_db()
        self.assertEqual(h2.status, 'accepted')


class EveryPageEveryRole(VacancyBase):
    """With one of everything in the database, open every page as every role: no 500s."""

    def test_no_page_crashes(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        v = self.publish(self.post_job())
        self.apply(v)
        self.hire(VacancyApplication.objects.get(vacancy=v))
        c = EmploymentContract.objects.get(vacancy=v)
        h = DirectHireRequest.objects.create(
            client=self.client_user, worker=self.wp2, title='x', description='x', location='x',
            duration_type='hours', duration_value=2, start_datetime=timezone.now(), offered_rate=D('5000'))

        skip = ('logout', 'delete', 'export', 'download', '/media/', 'websocket', '/admin/', 'api/docs', 'redoc',
                'docs.json', 'set_language', 'i18n', 'toggle', 'send', 'resend', 'verify-email', 'activate', 'reset')
        paths = set()

        def walk(patterns, prefix=''):
            for p in patterns:
                route = str(p.pattern)
                if isinstance(p, URLResolver):
                    walk(p.url_patterns, prefix + route)
                elif isinstance(p, URLPattern):
                    full = prefix + route
                    if '<' in full or '(?P' in full or '\\' in full or full.startswith('^'):
                        continue
                    paths.add('/' + full.lstrip('^').rstrip('$'))
        walk(get_resolver().url_patterns)
        paths = sorted(p for p in paths if not any(s in p for s in skip))
        details = [f'/services/client/request/{sr.id}/', f'/services/worker/assignment/{asg.id}/',
                   f'/dashboard/service-requests/{sr.id}/', f'/vacancies/{v.id}/', f'/vacancies/contracts/{c.id}/',
                   f'/jobs/direct-hire/{h.id}/', f'/api/vacancies/{v.id}/', f'/api/vacancies/contracts/{c.id}/',
                   f'/api/v1/client/service-requests/{sr.id}/', f'/api/v1/worker/my-assignments/{asg.id}/',
                   f'/dashboard/verification/{self.wp.id}/', f'/dashboard/workers/verify/{self.wp.id}/']
        agent_c = Client(); agent_c.force_login(self.agent_user)
        roles = {'anon': Client(), 'admin': self.admin_c, 'client': self.client_c, 'worker': self.worker_c, 'agent': agent_c}
        crashes = []
        for role, cl in roles.items():
            for p in paths + details:
                try:
                    r = cl.get(p)
                    if r.status_code >= 500:
                        crashes.append(f'{role} {p} -> {r.status_code}')
                except Exception as e:  # noqa: BLE001 - we want every failure listed
                    crashes.append(f'{role} {p} -> {type(e).__name__}: {e}')
        print(f'\nopened {len(paths) + len(details)} pages x {len(roles)} roles')
        self.assertEqual(crashes, [], '\n'.join(crashes))
