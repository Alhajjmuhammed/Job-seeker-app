"""
Regression tests for defects found in the component review: cancelled jobs
being accepted and paid, rejected workers blocking a request, payment
verification dispatching to cancelled requests, invoice/review abuse, search
leaks, and inputs that used to be 500s.
"""

from decimal import Decimal as D

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User
from clients.models import ClientProfile
from jobs.invoices import Invoice, InvoiceService
from jobs.models import DirectHireRequest, JobRequest
from jobs.reviews import Review
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from workers.models import WorkerDocument, WorkerProfile

from tests import test_full_flows as flows
from tests.test_full_flows import FlowBase, PNG, post_json


class QuickServiceFixTests(FlowBase):
    verify_payment = flows.AssignmentOptionTests.verify_payment

    def assign(self, sr, wp=None):
        wp = wp or self.wp
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': wp.id})
        self.assertIn(r.status_code, (200, 201), r.content)
        return ServiceRequestAssignment.objects.get(service_request=sr, worker=wp)

    def test_cancelled_assignment_cannot_be_accepted_or_completed(self):
        sr, _ = self.book()
        asg = self.assign(sr)
        sr.cancel('client changed mind')

        for url in (f'/api/v1/worker/my-assignments/{asg.id}/respond/',
                    f'/api/v1/worker/service-requests/{asg.id}/respond/'):
            r = post_json(self.worker_c, url, {'accepted': True})
            self.assertEqual(r.status_code, 400, (url, r.content))
        r = self.worker_c.post(f'/services/worker/assignment/{asg.id}/respond/', {'action': 'accept'})
        self.assertIn(r.status_code, (302, 404))
        self.assertFalse(asg.accept_assignment())
        self.assertFalse(asg.reject_assignment('x'))

        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/complete/', {})
        self.assertEqual(r.status_code, 400, r.content)
        asg.refresh_from_db(); sr.refresh_from_db(); self.wp.refresh_from_db()
        self.assertEqual(asg.status, 'cancelled')
        self.assertEqual(sr.status, 'cancelled')
        self.assertEqual(self.wp.total_earnings, 0)

    def test_cannot_clock_in_after_cancellation(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        sr.cancel('x')
        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/clock-in/', {})
        self.assertEqual(r.status_code, 400, r.content)

    def test_late_completion_never_reopens_a_cancelled_request(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        ServiceRequest.objects.filter(pk=sr.pk).update(status='cancelled')
        asg.refresh_from_db()
        self.assertFalse(asg.mark_completed())
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'cancelled')

    def test_rejection_frees_the_slot_and_returns_request_to_pending(self):
        sr, _ = self.book()
        asg = self.assign(sr)
        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/respond/',
                      {'accepted': False, 'rejection_reason': 'busy'})
        self.assertEqual(r.status_code, 200, r.content)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'pending')

        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/reassign/', {'worker_id': self.wp2.id})
        self.assertIn(r.status_code, (200, 201), r.content)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'assigned')

    def test_rejection_frees_the_slot_on_the_dashboard_assign(self):
        sr, _ = self.book()
        self.assertTrue(self.assign(sr).reject_assignment('busy'))
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/assign/', {'worker_id': self.wp2.id})
        self.assertTrue(ServiceRequestAssignment.objects.filter(
            service_request=sr, worker=self.wp2, status='pending').exists())

    def test_rejection_frees_the_slot_on_bulk_assign(self):
        sr, _ = self.book()
        self.assertTrue(self.assign(sr).reject_assignment('busy'))
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/bulk-assign/',
                      {'worker_ids': [self.wp2.id]})
        self.assertIn(r.status_code, (200, 201), r.content)

    def test_verifying_payment_on_cancelled_request_dispatches_nobody(self):
        sr, _ = self.book(assignment_mode='auto_nearest', latitude=-6.79, longitude=39.27)
        sr.cancel('x')
        sr.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        sr.save()
        r = self.admin_c.post(f'/dashboard/service-requests/{sr.id}/verify-payment/')
        self.assertEqual(r.status_code, 302)
        sr.refresh_from_db()
        self.assertFalse(sr.payment_verified)
        self.assertEqual(sr.assignments.count(), 0)
        # and the auto-assign itself refuses a closed request
        from clients.assignment_mode import apply_assignment_mode
        ServiceRequest.objects.filter(pk=sr.pk).update(payment_status='paid')
        sr.refresh_from_db()
        apply_assignment_mode(sr)
        self.assertEqual(sr.assignments.count(), 0)


class PaymentAndDirectHireFixTests(FlowBase):
    def test_bad_payment_amounts_are_400(self):
        for amount in ('abc', 'NaN', 'Infinity', '-5', '0'):
            r = post_json(self.client_c, '/api/v1/client/process-payment/',
                          {'amount': amount, 'payment_type': 'yas', 'phone_number': '+255711222333'})
            self.assertEqual(r.status_code, 400, (amount, r.content))

    def test_direct_hire_zero_duration_or_rate_is_a_form_error(self):
        WorkerDocument.objects.create(worker=self.wp, document_type='id', title='id',
                                      file=SimpleUploadedFile('i.png', PNG, 'image/png'))
        base = {'title': 'x', 'description': 'y', 'location': 'z', 'duration_type': 'hours',
                'start_datetime': '2026-12-01 10:00'}
        for extra in ({'duration_value': 0, 'offered_rate': '5000'},
                      {'duration_value': 2, 'offered_rate': '-5000'},
                      {'duration_value': 2, 'offered_rate': '0'}):
            r = self.client_c.post(f'/jobs/direct-hire/request/{self.wp.id}/', dict(base, **extra))
            self.assertEqual(r.status_code, 200, extra)
            self.assertTrue(r.context['form'].errors, extra)
        self.assertFalse(DirectHireRequest.objects.exists())
        r = self.client_c.post(f'/jobs/direct-hire/request/{self.wp.id}/',
                               dict(base, duration_value=2, offered_rate='5000'))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(DirectHireRequest.objects.get().total_amount, D('10000'))


class InvoiceFixTests(FlowBase):
    ITEMS = [{'description': 'x', 'quantity': 1, 'unit_price': 100}]

    def setUp(self):
        super().setUp()
        self.cp = self.client_user.client_profile
        sr = ServiceRequest.objects.create(
            client=self.client_user, category=self.cat, title='t', description='d', location='x', city='Dar',
            daily_rate=self.cat.daily_rate, service_fee=self.cat.service_fee, total_price=D('30000'),
            preferred_date=timezone.now().date(), workers_needed=1, status='completed')
        ServiceRequestAssignment.objects.create(service_request=sr, worker=self.wp, status='completed',
                                                worker_accepted=True)

    def create(self, **body):
        return post_json(self.worker_c, '/api/v1/job-invoices/create/',
                         {'client_id': self.cp.id, 'items': self.ITEMS, **body})

    def test_only_issuing_worker_or_staff_can_mark_paid(self):
        inv = InvoiceService.create_invoice(self.wp, self.cp, None, self.ITEMS)
        InvoiceService.mark_as_sent(inv)
        r = post_json(self.client_c, f'/api/v1/job-invoices/{inv.id}/paid/')
        self.assertEqual(r.status_code, 403)
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'sent')
        r = post_json(self.worker_c, f'/api/v1/job-invoices/{inv.id}/paid/')
        self.assertEqual(r.status_code, 200, r.content)

    def test_invoice_amounts_and_due_days_are_validated(self):
        for body in ({'discount': -5000}, {'discount': 101}, {'tax_rate': -1}, {'tax_rate': 150},
                     {'discount': 'abc'}, {'due_days': 'abc'}, {'due_days': -3}):
            r = self.create(**body)
            self.assertEqual(r.status_code, 400, (body, r.content))
        r = self.create(discount=10, tax_rate=10, due_days=14)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Invoice.objects.get().total, D('100.00'))

    def test_worker_can_only_invoice_a_client_they_worked_for(self):
        other_cp = self.other_client.client_profile
        r = post_json(self.worker_c, '/api/v1/job-invoices/create/', {'client_id': other_cp.id, 'items': self.ITEMS})
        self.assertEqual(r.status_code, 403)
        job = JobRequest.objects.create(client=self.other_client, title='j', description='d', location='l',
                                        city='c', budget=1, duration_days=1, workers_needed=1)
        r = self.create(job_id=job.id)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Invoice.objects.exists())

    def test_earnings_limits_never_500(self):
        w = self.worker_c
        self.assertEqual(w.get('/api/v1/worker-earnings/history/?limit=-1').status_code, 200)
        self.assertEqual(w.get('/api/v1/worker-earnings/clients/?limit=-1').status_code, 200)
        r = w.get('/api/v1/worker-earnings/breakdown/?periods=100000')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['periods'], 24)


class ReviewFixTests(FlowBase):
    def setUp(self):
        super().setUp()
        sr = ServiceRequest.objects.create(
            client=self.client_user, category=self.cat, title='t', description='d', location='x', city='Dar',
            daily_rate=self.cat.daily_rate, service_fee=self.cat.service_fee, total_price=D('30000'),
            preferred_date=timezone.now().date(), workers_needed=1, status='completed')
        ServiceRequestAssignment.objects.create(service_request=sr, worker=self.wp, status='completed',
                                                worker_accepted=True)

    def review(self, **body):
        return post_json(self.client_c, '/api/v1/job-reviews/', {'reviewee_id': self.worker_user.id, **body})

    def test_unrelated_job_ids_cannot_add_reviews(self):
        for i in range(3):
            job = JobRequest.objects.create(client=self.other_client, title=f'j{i}', description='d', location='l',
                                            city='c', budget=1, duration_days=1, workers_needed=1,
                                            status='completed')
            r = self.review(job_id=job.id, overall_rating=1)
            self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(self.review(overall_rating=4).status_code, 201)
        self.assertEqual(self.review(overall_rating=1).status_code, 400)  # one per job
        self.assertEqual(Review.objects.count(), 1)

    def test_job_the_two_did_together_is_accepted(self):
        job = JobRequest.objects.create(client=self.client_user, title='j', description='d', location='l',
                                        city='c', budget=1, duration_days=1, workers_needed=1,
                                        status='completed', assigned_worker=self.wp)
        self.assertEqual(self.review(job_id=job.id, overall_rating=5).status_code, 201)
        self.assertEqual(self.review(job_id=job.id, overall_rating=5).status_code, 400)

    def test_rating_strings_and_bad_limits(self):
        for bad in ('abc', 0, 6, True, None):
            self.assertEqual(self.review(overall_rating=bad).status_code, 400, bad)
        self.assertEqual(self.review(overall_rating=4, quality_rating='x').status_code, 400)
        self.assertEqual(self.review(overall_rating='5').status_code, 201)
        r = self.client_c.get(f'/api/v1/job-reviews/user/{self.worker_user.id}/?limit=abc&offset=-4')
        self.assertEqual(r.status_code, 200)


class SearchFixTests(FlowBase):
    def test_client_search_hides_unverified_workers(self):
        WorkerProfile.objects.filter(pk=self.wp2.pk).update(verification_status='pending')
        ids = [w['id'] for w in self.client_c.get('/api/jobs/search/workers/').json()['results']]
        self.assertIn(self.wp.id, ids)
        self.assertNotIn(self.wp2.id, ids)
        ids = [w['id'] for w in self.admin_c.get('/api/jobs/search/workers/').json()['results']]
        self.assertIn(self.wp2.id, ids)  # staff still see them

    def test_location_search_does_not_match_home_address(self):
        WorkerProfile.objects.filter(pk=self.wp.pk).update(address='42 Hidden Lane')
        r = self.client_c.get('/api/jobs/search/workers/?location=Hidden')
        self.assertEqual(r.json()['results'], [])
        r = self.client_c.get('/api/jobs/search/workers/?location=Dar')
        self.assertTrue(r.json()['results'])

    def test_bad_paging_never_500(self):
        for url in ('/api/jobs/search/?page=abc', '/api/jobs/search/?page_size=0',
                    '/api/jobs/search/workers/?page_size=0', '/api/jobs/search/workers/?page_size=-5&page=-1',
                    '/api/jobs/search/workers/?page=abc'):
            r = self.client_c.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertGreaterEqual(r.json()['page_size'], 1)

    def test_sort_by_rate_lists_each_worker_once(self):
        from workers.models import Category
        cat2 = Category.objects.create(name='Painter', daily_rate=D('10000'), service_fee=D('1000'))
        self.wp.categories.add(cat2)
        r = self.client_c.get('/api/v1/search/workers/?sort_by=rate')
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        workers = body.get('workers') or body.get('results', {}).get('workers')
        ids = [w['id'] for w in workers]
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertEqual(ids[0], self.wp.id)  # cheapest category first
