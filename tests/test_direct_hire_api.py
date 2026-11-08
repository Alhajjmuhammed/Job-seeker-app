"""
Direct hire from the app: a client books one worker straight away.

    python manage.py test tests.test_direct_hire_api
"""
from datetime import timedelta
from decimal import Decimal as D

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from clients.models import Rating
from jobs.models import DirectHireRequest
from worker_connect.notification_models import Notification
from workers.models import WorkerCustomSkill, WorkerDocument

from .test_full_flows import FlowBase, PNG, post_json

API = '/api/jobs/direct-hires/'


def body(worker, **extra):
    data = {
        'worker_id': worker.id, 'title': 'Fix the sink', 'description': 'Kitchen sink leaks',
        'location': 'Mikocheni, house 12', 'duration_type': 'hours', 'duration_value': 3,
        'start_datetime': (timezone.now() + timedelta(days=1)).isoformat(), 'offered_rate': '5000',
    }
    data.update(extra)
    return data


class DirectHireApiBase(FlowBase):
    def setUp(self):
        super().setUp()
        WorkerDocument.objects.create(worker=self.wp, document_type='id', title='ID',
                                      file=SimpleUploadedFile('i.png', PNG, 'image/png'))
        self.wp.availability = 'available'
        self.wp.save(update_fields=['availability'])

    def book(self, expect=201, **extra):
        r = post_json(self.client_c, API, body(self.wp, **extra))
        self.assertEqual(r.status_code, expect, r.content)
        return r

    def make(self, status='pending', client=None):
        return DirectHireRequest.objects.create(
            client=client or self.client_user, worker=self.wp, title='x', description='x', location='Secret st 5',
            duration_type='days', duration_value=2, start_datetime=timezone.now() + timedelta(days=1),
            offered_rate=D('20000'), status=status)


class CreateTests(DirectHireApiBase):
    def test_client_books_and_worker_is_told(self):
        r = self.book()
        data = r.json()
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(D(data['total_amount']), D('15000'))  # rate x 3 hours
        self.assertEqual(data['location'], 'Mikocheni, house 12')  # the client sees their own address
        self.assertTrue(data['can_cancel'])
        self.assertFalse(data['can_complete'] or data['can_chat'])
        self.assertEqual(data['worker']['phone'], '')  # not before the worker accepts
        hire = DirectHireRequest.objects.get(pk=data['id'])
        self.assertEqual((hire.client, hire.worker), (self.client_user, self.wp))
        self.assertTrue(Notification.objects.filter(recipient=self.worker_user,
                                                    extra_data__direct_hire_id=hire.id).exists())

    def test_refusals(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        for bad in ({'duration_value': 0}, {'offered_rate': '0'}, {'offered_rate': '-5'},
                    {'start_datetime': past}, {'title': ''}, {'duration_type': 'weeks'}):
            r = self.book(expect=400, **bad)
            self.assertIn('error', r.json())
            self.assertIsInstance(r.json()['error'], str)
        self.assertEqual(self.book(expect=404, worker_id=99999).json()['code'], 'worker_not_found')
        # a worker who is not verified (or has no ID) can't be booked
        r = post_json(self.client_c, API, body(self.wp2))
        self.assertEqual((r.status_code, r.json()['code']), (400, 'worker_not_eligible'))
        # only clients book
        r = post_json(self.worker_c, API, body(self.wp2))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(DirectHireRequest.objects.exists())


class ListAndDetailTests(DirectHireApiBase):
    def test_lists_for_both_roles(self):
        a, b = self.make(), self.make('accepted')
        mine = self.make(client=self.other_client)
        r = self.client_c.get(API)
        self.assertEqual(r.status_code, 200)
        ids = [x['id'] for x in r.json()['results']]
        self.assertEqual(ids, [b.id, a.id])  # newest first, only mine
        self.assertIn('count', r.json())
        self.assertEqual([x['id'] for x in self.client_c.get(API, {'status': 'accepted'}).json()['results']], [b.id])
        w = [x['id'] for x in self.worker_c.get(API).json()['results']]
        self.assertEqual(set(w), {a.id, b.id, mine.id})
        self.assertEqual(self.worker_c.get(API, {'status': 'rejected,cancelled'}).json()['count'], 0)
        other_worker = Client(); other_worker.force_login(self.worker2_user)
        self.assertEqual(other_worker.get(API).json()['count'], 0)

    def test_worker_list_status_param_defaults_to_pending(self):
        a, b = self.make(), self.make('accepted')
        r = self.worker_c.get('/api/workers/direct-hire-requests/')
        self.assertEqual([x['id'] for x in r.json()], [a.id])
        self.assertEqual(r.json()[0]['location'], '')  # address hidden until accepted
        r = self.worker_c.get('/api/workers/direct-hire-requests/', {'status': 'accepted'})
        self.assertEqual([x['id'] for x in r.json()], [b.id])
        self.assertEqual(r.json()[0]['location'], 'Secret st 5')
        self.assertEqual(len(self.worker_c.get('/api/workers/direct-hire-requests/', {'status': 'all'}).json()), 2)

    def test_detail_visibility(self):
        h = self.make()
        stranger = Client(); stranger.force_login(self.other_client)
        self.assertEqual(stranger.get(f'{API}{h.id}/').status_code, 404)
        w2 = Client(); w2.force_login(self.worker2_user)
        self.assertEqual(w2.get(f'{API}{h.id}/').status_code, 404)
        d = self.worker_c.get(f'{API}{h.id}/').json()
        self.assertEqual((d['location'], d['location_hidden'], d['client']['phone']), ('', True, ''))
        self.assertTrue(d['can_accept'] and d['can_decline'])
        self.assertFalse(d['can_cancel'] or d['can_chat'] or d['can_complete'])
        self.assertEqual(d['my_role'], 'worker')
        h.status = 'accepted'
        h.save()
        d = self.worker_c.get(f'{API}{h.id}/').json()
        self.assertEqual((d['location'], d['client']['phone']), ('Secret st 5', '+255711222333'))
        self.assertTrue(d['can_chat'] and d['can_cancel'])
        c = self.client_c.get(f'{API}{h.id}/').json()
        self.assertEqual(c['worker']['phone'], '0744555666')
        self.assertTrue(c['can_complete'])


class AnswerCompleteCancelTests(DirectHireApiBase):
    def test_accept_then_complete_with_rating(self):
        h = self.make()
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h.id}/accept/')
        self.assertEqual(r.status_code, 200, r.content)
        h.refresh_from_db(); self.wp.refresh_from_db()
        self.assertEqual((h.status, self.wp.availability), ('accepted', 'busy'))
        # accepting twice is refused
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h.id}/accept/')
        self.assertEqual((r.status_code, r.json()['code']), (400, 'already_responded'))
        # the worker can't complete
        self.assertEqual(post_json(self.worker_c, f'{API}{h.id}/complete/', {'rating': 5}).status_code, 403)
        r = post_json(self.client_c, f'{API}{h.id}/complete/', {'rating': 4, 'feedback': 'Good work'})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['status'], r.json()['client_rating']), ('completed', 4))
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.availability, 'available')
        self.assertEqual(self.wp.total_earnings, D('40000'))
        self.assertEqual(self.wp.completed_jobs, 1)
        self.assertEqual(Rating.objects.get(client=self.client_user, worker=self.wp).rating, 4)
        self.assertEqual(float(self.wp.average_rating), 4.0)
        # completing twice is refused; a bad rating is just "no rating"
        self.assertEqual(post_json(self.client_c, f'{API}{h.id}/complete/', {'rating': 5}).status_code, 400)
        h2 = self.make('accepted')
        r = post_json(self.client_c, f'{API}{h2.id}/complete/', {'rating': 'abc'})
        self.assertEqual((r.status_code, r.json()['client_rating']), (200, None))

    def test_busy_worker_cannot_accept_but_can_decline_with_reason(self):
        h = self.make()
        self.wp.availability = 'busy'
        self.wp.save(update_fields=['availability'])
        d = self.worker_c.get(f'{API}{h.id}/').json()
        self.assertTrue(d['worker_busy'])
        self.assertFalse(d['can_accept'])
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h.id}/accept/')
        self.assertEqual((r.status_code, r.json()['code']), (400, 'worker_busy'))
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h.id}/reject/',
                      {'reason': 'Away that week'})
        self.assertEqual(r.status_code, 200, r.content)
        h.refresh_from_db()
        self.assertEqual((h.status, h.worker_response_message), ('rejected', 'Away that week'))
        self.assertTrue(Notification.objects.filter(recipient=self.client_user,
                                                    extra_data__direct_hire_id=h.id).exists())
        # someone else can't answer it
        h2 = self.make()
        w2 = Client(); w2.force_login(self.worker2_user)
        self.assertEqual(post_json(w2, f'/api/jobs/worker/direct-hire-requests/{h2.id}/reject/').status_code, 404)

    def test_cancel(self):
        h = self.make()
        # the worker can't cancel a pending one (they decline instead), a stranger gets 404
        self.assertEqual(post_json(self.worker_c, f'/api/jobs/direct-hire-requests/{h.id}/cancel/').status_code, 400)
        stranger = Client(); stranger.force_login(self.other_client)
        self.assertEqual(post_json(stranger, f'/api/jobs/direct-hire-requests/{h.id}/cancel/').status_code, 404)
        r = post_json(self.client_c, f'/api/jobs/direct-hire-requests/{h.id}/cancel/', {'reason': 'Fixed it myself'})
        self.assertEqual(r.status_code, 200, r.content)
        d = self.client_c.get(f'{API}{h.id}/').json()
        self.assertEqual(d['status'], 'cancelled')
        self.assertIn('Fixed it myself', d['worker_response_message'])
        self.assertFalse(d['can_cancel'])
        # after accepting, the worker may cancel - and is free again
        h2 = self.make()
        post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{h2.id}/accept/')
        r = post_json(self.worker_c, f'/api/jobs/direct-hire-requests/{h2.id}/cancel/', {'reason': 'Sick'})
        self.assertEqual(r.status_code, 200, r.content)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.availability, 'available')


class WebsiteStillWorksTests(DirectHireApiBase):
    def test_website_flow_on_the_shared_rules(self):
        start = (timezone.localtime() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        r = self.client_c.post(f'/jobs/direct-hire/request/{self.wp.id}/', {
            'title': 'Paint', 'description': 'Two rooms', 'location': 'Mbezi', 'duration_type': 'days',
            'duration_value': 2, 'start_datetime': start, 'offered_rate': '30000'})
        self.assertEqual(r.status_code, 302, r.content[:400])
        h = DirectHireRequest.objects.get()
        # a past start is refused on the website too
        past = (timezone.localtime() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        r = self.client_c.post(f'/jobs/direct-hire/request/{self.wp.id}/', {
            'title': 'P', 'description': 'D', 'location': 'M', 'duration_type': 'days',
            'duration_value': 2, 'start_datetime': past, 'offered_rate': '30000'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        # the worker declines a second one with a reason on the website, accepts the first
        h2 = self.make()
        self.worker_c.post(f'/jobs/direct-hire/{h2.id}/reject/', {'reason': 'Too far'})
        h2.refresh_from_db()
        self.assertEqual((h2.status, h2.worker_response_message), ('rejected', 'Too far'))
        r = self.worker_c.post(f'/jobs/direct-hire/{h.id}/accept/', {'response_message': 'ok'})
        self.assertEqual(r.status_code, 302)
        h.refresh_from_db()
        self.assertEqual(h.status, 'accepted')
        # what the website did shows in the app
        self.assertEqual(self.worker_c.get(f'{API}{h.id}/').json()['location'], 'Mbezi')
        self.client_c.post(f'/jobs/direct-hire/{h.id}/complete/', {'rating': 5, 'feedback': 'great'})
        h.refresh_from_db(); self.wp.refresh_from_db()
        self.assertEqual((h.status, h.client_rating, self.wp.availability), ('completed', 5, 'available'))
        for url in (f'/jobs/direct-hire/{h.id}/', '/jobs/direct-hires/'):
            self.assertEqual(self.client_c.get(url).status_code, 200, url)


class CustomSkillApiTests(FlowBase):
    URL = '/api/workers/custom-skills/'

    def test_add_list_duplicate_delete(self):
        r = post_json(self.worker_c, self.URL, {'name': ' Solar panel installation ', 'years_of_experience': 3})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['name'], 'Solar panel installation')
        r = post_json(self.worker_c, self.URL, {'name': 'solar PANEL installation'})
        self.assertEqual((r.status_code, r.json()['code']), (400, 'skill_exists'))
        self.assertEqual(post_json(self.worker_c, self.URL, {'name': ''}).status_code, 400)
        items = self.worker_c.get(self.URL).json()['results']
        self.assertEqual([s['name'] for s in items], ['Solar panel installation'])
        self.assertEqual(post_json(self.client_c, self.URL, {'name': 'x'}).status_code, 403)
        sid = items[0]['id']
        w2 = Client(); w2.force_login(self.worker2_user)
        self.assertEqual(w2.delete(f'{self.URL}{sid}/').status_code, 404)
        self.assertEqual(self.worker_c.delete(f'{self.URL}{sid}/').status_code, 200)
        self.assertFalse(WorkerCustomSkill.objects.exists())

    def test_website_add_still_works(self):
        self.worker_c.post('/workers/custom-skills/add/', {'name': 'Tiling', 'years_of_experience': 1})
        self.worker_c.post('/workers/custom-skills/add/', {'name': 'tiling', 'years_of_experience': 1})
        self.assertEqual(WorkerCustomSkill.objects.filter(worker=self.wp).count(), 1)
