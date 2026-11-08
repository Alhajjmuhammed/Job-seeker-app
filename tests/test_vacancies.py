"""
Job posts (vacancies): a company or a household posts a long-term job, the
admin reviews it, workers apply, the poster hires, a contract runs.
Every rule is checked through the app API, and the main pages on the website.
"""
from datetime import timedelta

from django.core import mail
from django.test import Client
from django.utils import timezone

from accounts.models import User
from jobs.chat_access import call_number, can_chat
from jobs.models import Report
from jobs.vacancy_models import EmploymentContract, Vacancy, VacancyApplication
from jobs.vacancy_service import daily_maintenance
from worker_connect.notification_models import Notification
from workers.models import WorkerProfile

from .test_full_flows import PW, FlowBase, post_json, patch_json

API = '/api/vacancies/'


def job_body(**extra):
    today = timezone.localdate()
    body = {
        'kind': 'home', 'category': None, 'title': 'House girl needed', 'description': 'Cooking and cleaning',
        'worker_type_needed': 'any', 'workers_needed': 1, 'duration': '3_months',
        'start_date': str(today + timedelta(days=7)), 'closing_date': str(today + timedelta(days=5)),
        'salary_amount': '250000', 'pay_period': 'month', 'city': 'Dar', 'area': 'Mbezi',
        'address': 'Plot 7, Secret Lane', 'live_in': True, 'food_provided': True, 'room_provided': True,
        'duties': 'Cook, clean, wash clothes', 'trial_period': '2 weeks', 'verification_number': '19900101-12345',
    }
    body.update(extra)
    return body


class VacancyBase(FlowBase):
    def post_job(self, c=None, **extra):
        r = post_json(c or self.client_c, API, job_body(category=self.cat.id, **extra))
        self.assertEqual(r.status_code, 201, r.content)
        return Vacancy.objects.get(pk=r.json()['id'])

    def publish(self, v):
        r = post_json(self.admin_c, f'{API}{v.id}/review/', {'action': 'publish'})
        self.assertEqual(r.status_code, 200, r.content)
        v.refresh_from_db()
        return v

    def apply(self, v, c=None, expect=201):
        r = post_json(c or self.worker_c, f'{API}{v.id}/apply/', {'message': 'I have 3 years experience'})
        self.assertEqual(r.status_code, expect, r.content)
        return r

    def hire(self, app, c=None, expect=201):
        r = post_json(c or self.client_c, f'{API}applications/{app.id}/hire/', {})
        self.assertEqual(r.status_code, expect, r.content)
        return r

    def worker2(self):
        c = Client(); c.force_login(self.worker2_user)
        return c


class PostAndReviewTests(VacancyBase):
    def test_new_post_waits_for_review_and_is_hidden(self):
        v = self.post_job()
        self.assertEqual(v.status, 'review')
        self.assertTrue(any(n.extra_data.get('vacancy_id') == v.id
                            for n in Notification.objects.filter(recipient=self.admin)))
        self.assertNotIn(b'House girl', self.worker_c.get(API).content)
        self.assertEqual(self.worker_c.get(f'{API}{v.id}/').status_code, 404)
        self.apply(v, expect=404)

    def test_only_clients_post(self):
        for c in (self.worker_c, self.admin_c):
            r = post_json(c, API, job_body(category=self.cat.id))
            self.assertEqual(r.status_code, 403, r.content)
        agent = Client(); agent.force_login(self.agent_user)
        self.assertEqual(post_json(agent, API, job_body(category=self.cat.id)).status_code, 403)

    def test_form_checks(self):
        past = str(timezone.localdate() - timedelta(days=1))
        for bad in ({'closing_date': past}, {'start_date': past}, {'kind': 'business', 'company_name': ''},
                    {'verification_number': ''}, {'salary_amount': '100', 'salary_max': '50'},
                    {'workers_needed': 0}, {'category': ''}):
            r = post_json(self.client_c, API, job_body(category=self.cat.id, **bad) if 'category' not in bad
                          else job_body(**bad))
            self.assertEqual(r.status_code, 400, (bad, r.content))
            self.assertIn('error', r.json())
        self.assertEqual(Vacancy.objects.count(), 0)

    def test_company_post_drops_home_only_fields(self):
        v = self.post_job(kind='business', company_name='Sea Cliff Hotel', workers_needed=5)
        self.assertFalse(v.live_in or v.food_provided or v.room_provided)
        self.assertEqual(v.poster_display_name, 'Sea Cliff Hotel')

    def test_review_needs_a_reason_to_send_back_or_reject(self):
        v = self.post_job()
        for action in ('changes', 'reject'):
            r = post_json(self.admin_c, f'{API}{v.id}/review/', {'action': action})
            self.assertEqual(r.status_code, 400)
        r = post_json(self.admin_c, f'{API}{v.id}/review/', {'action': 'changes', 'note': 'Add the salary range'})
        self.assertEqual(r.status_code, 200)
        v.refresh_from_db(); self.assertEqual(v.status, 'changes')
        self.assertEqual(self.client_c.get(f'{API}{v.id}/').json()['review_note'], 'Add the salary range')

    def test_only_admin_reviews(self):
        v = self.post_job()
        for c in (self.client_c, self.worker_c):
            self.assertEqual(post_json(c, f'{API}{v.id}/review/', {'action': 'publish'}).status_code, 403)
        self.assertEqual(self.client_c.get(f'{API}review/').status_code, 403)
        self.assertEqual(len(self.admin_c.get(f'{API}review/').json()['results']), 1)

    def test_edit_goes_back_to_review_but_published_cannot_be_edited(self):
        v = self.post_job()
        post_json(self.admin_c, f'{API}{v.id}/review/', {'action': 'reject', 'note': 'Unclear'})
        r = patch_json(self.client_c, f'{API}{v.id}/', {'title': 'House girl, live-in'})
        self.assertEqual(r.status_code, 200, r.content)
        v.refresh_from_db()
        self.assertEqual((v.status, v.title, v.city), ('review', 'House girl, live-in', 'Dar'))
        self.publish(v)
        self.assertEqual(patch_json(self.client_c, f'{API}{v.id}/', {'title': 'x'}).status_code, 403)
        other = Client(); other.force_login(self.other_client)
        self.assertEqual(patch_json(other, f'{API}{v.id}/', {'title': 'x'}).status_code, 404)

    def test_publish_alerts_matching_workers_without_email(self):
        v = self.post_job()
        far = User.objects.create_user(email='far@t.co', username='far', password=PW, user_type='worker')
        WorkerProfile.objects.create(user=far, verification_status='verified', city='Arusha').categories.add(self.cat)
        unverified = User.objects.create_user(email='unv@t.co', username='unv', password=PW, user_type='worker')
        WorkerProfile.objects.create(user=unverified, verification_status='pending', city='Dar').categories.add(self.cat)
        mail.outbox.clear()
        self.publish(v)
        alerted = {n.recipient_id for n in Notification.objects.filter(title='New job for you')}
        self.assertEqual(alerted, {self.worker_user.id, self.worker2_user.id})
        self.assertFalse([m for m in mail.outbox if 'New job for you' in m.subject])
        self.assertIn(b'House girl', self.worker_c.get(API).content)

    def test_job_type_filter_for_alerts(self):
        v = self.post_job(worker_type_needed='professional')
        self.wp.worker_type = 'professional'; self.wp.save()
        self.publish(v)
        alerted = {n.recipient_id for n in Notification.objects.filter(title='New job for you')}
        self.assertEqual(alerted, {self.worker_user.id})


class ApplyTests(VacancyBase):
    def setUp(self):
        super().setUp()
        self.v = self.publish(self.post_job())

    def test_list_hides_private_details(self):
        body = self.worker_c.get(API).content
        self.assertIn(b'Mbezi', body)
        for secret in (b'Secret Lane', b'19900101', b'+255711222333'):
            self.assertNotIn(secret, body)
        d = self.worker_c.get(f'{API}{self.v.id}/').json()
        self.assertNotIn('address', d); self.assertNotIn('poster_phone', d); self.assertNotIn('verification_number', d)
        self.assertIsNone(d['apply_problem'])

    def test_clients_cannot_browse_or_apply(self):
        self.assertEqual(self.client_c.get(API).status_code, 403)
        other = Client(); other.force_login(self.other_client)
        self.assertEqual(other.get(f'{API}{self.v.id}/').status_code, 404)
        self.apply(self.v, c=other, expect=404)

    def test_apply_rules(self):
        self.apply(self.v)
        self.assertEqual(self.apply(self.v, expect=400).json()['error'], 'You have already applied for this job.')
        self.wp2.verification_status = 'pending'; self.wp2.save()
        self.assertIn('verified', self.apply(self.v, c=self.worker2(), expect=400).json()['error'])

    def test_worker_type_must_match(self):
        v = self.publish(self.post_job(worker_type_needed='professional'))
        self.assertIn('Professional', self.apply(v, expect=400).json()['error'])
        self.wp.worker_type = 'professional'; self.wp.save()
        self.apply(v)

    def test_closed_job_takes_no_applications(self):
        self.assertEqual(post_json(self.client_c, f'{API}{self.v.id}/close/').status_code, 200)
        self.apply(self.v, expect=404)  # a closed job is no longer shown to workers who did not apply

    def test_poster_is_told_and_sees_applicant_without_phone(self):
        self.apply(self.v)
        self.assertTrue(Notification.objects.filter(recipient=self.client_user, notification_type='job_application').exists())
        r = self.client_c.get(f'{API}{self.v.id}/applications/')
        self.assertEqual(r.status_code, 200)
        row = r.json()['results'][0]
        self.assertEqual(row['worker']['name'], 'Wor Ker')
        self.assertNotIn(b'0744555666', r.content)
        other = Client(); other.force_login(self.other_client)
        self.assertEqual(other.get(f'{API}{self.v.id}/applications/').status_code, 404)
        self.assertEqual(self.worker2().get(f'{API}{self.v.id}/applications/').status_code, 404)

    def test_withdraw_and_apply_again(self):
        app = VacancyApplication.objects.get(pk=self.apply(self.v).json()['id'])
        self.assertEqual(post_json(self.worker2(), f'{API}applications/{app.id}/withdraw/').status_code, 404)
        self.assertEqual(post_json(self.worker_c, f'{API}applications/{app.id}/withdraw/').status_code, 200)
        self.apply(self.v)
        app.refresh_from_db(); self.assertEqual(app.status, 'applied')
        self.assertEqual(len(self.worker_c.get(f'{API}my-applications/').json()['results']), 1)


class HireAndContractTests(VacancyBase):
    def setUp(self):
        super().setUp()
        self.v = self.publish(self.post_job())
        self.app = VacancyApplication.objects.get(pk=self.apply(self.v).json()['id'])

    def test_hire_makes_a_contract_and_opens_chat_and_contact(self):
        self.assertFalse(can_chat(self.client_user, self.worker_user))
        self.assertEqual(call_number(self.worker_user, self.client_user), '')
        c = self.hire(self.app).json()
        contract = EmploymentContract.objects.get(pk=c['id'])
        self.assertEqual(contract.start_date, self.v.start_date)
        self.assertEqual(contract.end_date, self.v.start_date + timedelta(days=91))
        self.assertEqual(c['other_phone'], '0744555666')
        self.wp.refresh_from_db(); self.assertEqual(self.wp.availability, 'busy')
        self.v.refresh_from_db(); self.assertEqual(self.v.status, 'filled')
        self.assertTrue(can_chat(self.client_user, self.worker_user))
        self.assertEqual(call_number(self.worker_user, self.client_user), '+255711222333')
        d = self.worker_c.get(f'{API}{self.v.id}/').json()
        self.assertEqual((d['address'], d['poster_phone']), ('Plot 7, Secret Lane', '+255711222333'))
        self.assertTrue(Notification.objects.filter(recipient=self.worker_user, title='You are hired!').exists())
        self.assertEqual(self.worker2().get(f'{API}contracts/{contract.id}/').status_code, 404)

    def test_filling_the_last_place_turns_down_the_rest(self):
        other = VacancyApplication.objects.get(pk=self.apply(self.v, c=self.worker2()).json()['id'])
        self.hire(self.app)
        other.refresh_from_db()
        self.assertEqual(other.status, 'not_selected')
        self.assertTrue(Notification.objects.filter(recipient=self.worker2_user, notification_type='job_rejected').exists())
        self.assertIn('not open', self.hire(other, expect=400).json()['error'])

    def test_several_places(self):
        v = self.publish(self.post_job(kind='business', company_name='Hotel', workers_needed=2))
        a1 = VacancyApplication.objects.get(pk=self.apply(v).json()['id'])
        a2 = VacancyApplication.objects.get(pk=self.apply(v, c=self.worker2()).json()['id'])
        self.hire(a1)
        v.refresh_from_db(); self.assertEqual((v.status, v.places_left), ('published', 1))
        self.hire(a2)
        v.refresh_from_db(); self.assertEqual((v.status, v.places_left), ('filled', 0))

    def test_hire_start_date_cannot_be_past(self):
        r = post_json(self.client_c, f'{API}applications/{self.app.id}/hire/',
                      {'start_date': str(timezone.localdate() - timedelta(days=2))})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(EmploymentContract.objects.exists())

    def test_shortlist_and_not_selected(self):
        self.assertEqual(post_json(self.client_c, f'{API}applications/{self.app.id}/shortlist/').status_code, 200)
        self.app.refresh_from_db(); self.assertEqual(self.app.status, 'shortlisted')
        self.assertEqual(post_json(self.client_c, f'{API}applications/{self.app.id}/reject/').status_code, 200)
        self.app.refresh_from_db(); self.assertEqual(self.app.status, 'not_selected')
        self.hire(self.app, expect=400)

    def test_worker_cannot_hire_themselves_and_strangers_cannot_hire(self):
        self.hire(self.app, c=self.worker_c, expect=400)
        other = Client(); other.force_login(self.other_client)
        self.hire(self.app, c=other, expect=404)
        self.assertFalse(EmploymentContract.objects.exists())

    def test_admin_can_hire_for_the_poster(self):
        self.hire(self.app, c=self.admin_c)
        self.assertTrue(Notification.objects.filter(recipient=self.client_user, title='Worker hired').exists())

    def test_end_early_closes_chat_and_frees_worker(self):
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        self.assertEqual(post_json(self.worker_c, f'{API}contracts/{contract.id}/end/', {}).status_code, 400)
        r = post_json(self.worker_c, f'{API}contracts/{contract.id}/end/', {'reason': 'Family emergency'})
        self.assertEqual(r.status_code, 200, r.content)
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'ended_early')
        self.assertFalse(can_chat(self.client_user, self.worker_user))
        self.wp.refresh_from_db(); self.assertEqual(self.wp.availability, 'available')
        self.assertTrue(Notification.objects.filter(recipient=self.client_user, title='Contract ended').exists())
        d = self.worker_c.get(f'{API}contracts/{contract.id}/').json()
        self.assertNotIn('address', d); self.assertNotIn('other_phone', d)

    def test_renew(self):
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        self.assertEqual(post_json(self.worker_c, f'{API}contracts/{contract.id}/renew/', {'duration': '6_months'}).status_code, 400)
        r = post_json(self.client_c, f'{API}contracts/{contract.id}/renew/', {'duration': '6_months'})
        self.assertEqual(r.status_code, 200, r.content)
        new = EmploymentContract.objects.get(pk=r.json()['id'])
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'renewed')
        self.assertEqual((new.start_date, new.end_date), (contract.end_date, contract.end_date + timedelta(days=182)))
        self.assertEqual(new.renewed_from_id, contract.id)
        self.assertEqual(post_json(self.client_c, f'{API}contracts/{contract.id}/renew/', {'duration': '6_months'}).status_code, 400)
        self.assertTrue(can_chat(self.client_user, self.worker_user))

    def test_rate_after_the_end_once_each(self):
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        url = f'{API}contracts/{contract.id}/rate/'
        self.assertEqual(post_json(self.client_c, url, {'rating': 5}).status_code, 400)  # still active
        EmploymentContract.objects.filter(pk=contract.pk).update(status='finished')
        self.assertEqual(post_json(self.client_c, url, {'rating': 9}).status_code, 400)
        self.assertEqual(post_json(self.client_c, url, {'rating': 5, 'feedback': 'Great'}).status_code, 200)
        self.assertEqual(post_json(self.client_c, url, {'rating': 4}).status_code, 400)
        self.assertEqual(post_json(self.worker_c, url, {'rating': 4}).status_code, 200)
        contract.refresh_from_db()
        self.assertEqual((contract.employer_rating, contract.worker_rating), (5, 4))

    def test_reports(self):
        r = post_json(self.worker_c, f'{API}{self.v.id}/report/', {'report_type': 'fraud', 'description': 'Asked for money'})
        self.assertEqual(r.status_code, 201, r.content)
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        r = post_json(self.client_c, f'{API}contracts/{contract.id}/report/', {'report_type': 'safety_concern',
                                                                              'description': 'Did not come'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(set(Report.objects.values_list('content_type', flat=True)), {'job', 'contract'})
        self.assertEqual(Report.objects.get(content_type='contract').reported_user, self.worker_user)
        self.assertEqual(post_json(self.worker2(), f'{API}contracts/{contract.id}/report/',
                                   {'report_type': 'other', 'description': 'x'}).status_code, 404)
        self.assertEqual(post_json(self.worker_c, f'{API}{self.v.id}/report/', {'report_type': 'fraud'}).status_code, 400)

    def test_daily_upkeep(self):
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        other = self.publish(self.post_job(title='Guard'))
        a = VacancyApplication.objects.get(pk=self.apply(other, c=self.worker2()).json()['id'])
        # a week before the end: one reminder for each side, only once
        r = daily_maintenance(today=contract.end_date - timedelta(days=3))
        self.assertEqual((r['reminded'], r['closed']), (1, 1))  # the Guard job closed days ago too
        self.assertEqual(daily_maintenance(today=contract.end_date - timedelta(days=2))['reminded'], 0)
        # past the closing date of the open job and the end of the contract
        r = daily_maintenance(today=contract.end_date + timedelta(days=1))
        self.assertEqual((r['closed'], r['finished']), (0, 1))
        other.refresh_from_db(); a.refresh_from_db(); contract.refresh_from_db()
        self.assertEqual((other.status, a.status, contract.status), ('closed', 'not_selected', 'finished'))

    def test_notification_links(self):
        contract = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        n = Notification.objects.filter(recipient=self.worker_user, title='You are hired!').first()
        self.assertEqual(n.target_url, f'/vacancies/contracts/{contract.id}/')
        n = Notification.objects.filter(recipient=self.client_user, notification_type='job_application').first()
        self.assertEqual(n.target_url, f'/vacancies/{self.v.id}/')


class WebPagesTests(VacancyBase):
    """The website pages render for each role and the main actions work."""

    def test_pages_render(self):
        v = self.publish(self.post_job())
        app = VacancyApplication.objects.get(pk=self.apply(v).json()['id'])
        contract = EmploymentContract.objects.get(pk=self.hire(app).json()['id'])
        pages = {
            self.client_c: ['/vacancies/post/', '/vacancies/mine/', f'/vacancies/{v.id}/', '/vacancies/contracts/',
                            f'/vacancies/contracts/{contract.id}/'],
            self.worker_c: ['/vacancies/', '/vacancies/my-applications/', f'/vacancies/{v.id}/',
                            '/vacancies/contracts/', f'/vacancies/contracts/{contract.id}/'],
            self.admin_c: ['/vacancies/review/', '/vacancies/all/', f'/vacancies/{v.id}/',
                           f'/vacancies/contracts/{contract.id}/'],
        }
        for c, urls in pages.items():
            for url in urls:
                r = c.get(url, secure=True)
                self.assertEqual(r.status_code, 200, url)

    def test_strangers_get_404(self):
        v = self.post_job()
        other = Client(); other.force_login(self.other_client)
        for url in (f'/vacancies/{v.id}/', f'/vacancies/{v.id}/edit/'):
            self.assertEqual(other.get(url, secure=True).status_code, 404, url)
        self.assertEqual(self.worker_c.get(f'/vacancies/{v.id}/', secure=True).status_code, 404)  # not published yet
        self.assertEqual(self.client_c.get('/vacancies/review/', secure=True).status_code, 404)

    def test_full_flow_on_the_website(self):
        body = job_body(category=self.cat.id)
        body['live_in'] = 'on'; body['food_provided'] = 'on'; body['room_provided'] = ''
        r = self.client_c.post('/vacancies/post/', body, secure=True)
        self.assertEqual(r.status_code, 302, r.content[:500])
        v = Vacancy.objects.get()
        self.assertEqual((v.status, v.live_in, v.room_provided), ('review', True, False))
        r = self.admin_c.post(f'/vacancies/{v.id}/review/', {'action': 'publish'}, secure=True)
        self.assertEqual(r.status_code, 302)
        v.refresh_from_db(); self.assertEqual(v.status, 'published')
        self.worker_c.post(f'/vacancies/{v.id}/apply/', {'message': 'Hello'}, secure=True)
        app = VacancyApplication.objects.get()
        r = self.client_c.post(f'/vacancies/applications/{app.id}/hire/', {}, secure=True)
        contract = EmploymentContract.objects.get()
        self.assertRedirects(r, f'/vacancies/contracts/{contract.id}/', fetch_redirect_response=False)
        r = self.client_c.post(f'/vacancies/contracts/{contract.id}/end/', {'reason': 'Moving away'}, secure=True)
        contract.refresh_from_db(); self.assertEqual(contract.status, 'ended_early')


class ReviewFindingTests(VacancyBase):
    """Problems found by the independent review - each one stays fixed."""

    def setUp(self):
        super().setUp()
        self.v = self.publish(self.post_job())
        self.app = VacancyApplication.objects.get(pk=self.apply(self.v).json()['id'])

    def test_ending_early_after_a_renewal_closes_chat_contact_and_address(self):
        first = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        new_id = post_json(self.client_c, f'{API}contracts/{first.id}/renew/', {'duration': '6_months'}).json()['id']
        r = post_json(self.client_c, f'{API}contracts/{new_id}/end/', {'reason': 'Theft'})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(can_chat(self.client_user, self.worker_user))
        self.assertEqual(call_number(self.worker_user, self.client_user), '')
        self.assertNotIn('address', self.worker_c.get(f'{API}{self.v.id}/').json())
        old = self.worker_c.get(f'{API}contracts/{first.id}/').json()
        self.assertNotIn('address', old); self.assertNotIn('other_phone', old)
        self.assertFalse(old['relationship_open'])
        page = self.worker_c.get(f'/vacancies/contracts/{first.id}/', secure=True)
        self.assertNotContains(page, 'Secret Lane')
        self.assertEqual(post_json(self.client_c, f'{API}contracts/{first.id}/renew/', {'duration': '3_months'}).status_code, 400)

    def test_website_contract_hides_address_after_early_end(self):
        c = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        self.assertContains(self.worker_c.get(f'/vacancies/contracts/{c.id}/', secure=True), 'Secret Lane')
        post_json(self.worker_c, f'{API}contracts/{c.id}/end/', {'reason': 'Leaving'})
        self.assertNotContains(self.worker_c.get(f'/vacancies/contracts/{c.id}/', secure=True), 'Secret Lane')
        self.assertContains(self.admin_c.get(f'/vacancies/contracts/{c.id}/', secure=True), 'Secret Lane')

    def test_bad_filters_and_bodies_do_not_crash(self):
        self.assertEqual(self.worker_c.get(API, {'category': 'abc'}).status_code, 200)
        self.assertEqual(self.worker_c.get('/vacancies/', {'category': 'abc'}, secure=True).status_code, 200)
        c = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        self.assertEqual(post_json(self.client_c, f'{API}contracts/{c.id}/renew/', {'duration': ['x']}).status_code, 400)
        self.assertEqual(post_json(self.client_c, f'{API}contracts/{c.id}/rate/', {'rating': 'abc'}).status_code, 400)

    def test_withdraw_after_hire_is_refused(self):
        self.hire(self.app)
        self.assertEqual(post_json(self.worker_c, f'{API}applications/{self.app.id}/withdraw/').status_code, 400)
        self.app.refresh_from_db(); self.assertEqual(self.app.status, 'hired')

    def test_early_end_gives_the_place_back(self):
        c = EmploymentContract.objects.get(pk=self.hire(self.app).json()['id'])
        self.v.refresh_from_db(); self.assertEqual(self.v.status, 'filled')
        post_json(self.client_c, f'{API}contracts/{c.id}/end/', {'reason': 'Did not come'})
        self.v.refresh_from_db(); self.app.refresh_from_db()
        self.assertEqual((self.v.status, self.v.places_left, self.app.status), ('published', 1, 'ended'))
        self.assertTrue(Notification.objects.filter(recipient=self.client_user, title='A place is open again').exists())
        other = VacancyApplication.objects.get(pk=self.apply(self.v, c=self.worker2()).json()['id'])
        self.hire(other)

    def test_ending_a_permanent_job_is_a_normal_finish(self):
        v = self.publish(self.post_job(title='Gardener', duration='permanent'))
        a = VacancyApplication.objects.get(pk=self.apply(v, c=self.worker2()).json()['id'])
        c = EmploymentContract.objects.get(pk=self.hire(a).json()['id'])
        self.assertIsNone(c.end_date)
        post_json(self.worker2(), f'{API}contracts/{c.id}/end/', {'reason': 'Moving to Arusha'})
        c.refresh_from_db(); a.refresh_from_db()
        self.assertEqual((c.status, a.status), ('finished', 'hired'))

    def test_lists_do_not_run_a_query_per_row(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count(c, url):
            with CaptureQueriesContext(connection) as q:
                self.assertEqual(c.get(url).status_code, 200, url)
            return len(q)

        urls = [(self.worker_c, API), (self.worker_c, f'{API}my-applications/'), (self.client_c, f'{API}mine/'),
                (self.client_c, f'{API}{self.v.id}/applications/'), (self.client_c, f'{API}contracts/')]
        self.hire(self.app)
        before = {u: count(c, u) for c, u in urls}
        for i in range(4):  # four more jobs, each applied for and hired
            v = self.publish(self.post_job(title=f'Job {i}', duration='one_off'))  # one long contract at a time
            a = VacancyApplication.objects.get(pk=self.apply(v).json()['id'])
            self.hire(a)
        self.wp.verification_status = 'verified'; self.wp.save()
        extra = self.publish(self.post_job(title='Open one'))
        self.apply(extra, c=self.worker2())
        after = {u: count(c, u) for c, u in urls}
        for u in before:
            self.assertLessEqual(after[u] - before[u], 2, (u, before[u], after[u]))


class ListOrderTests(VacancyBase):
    def test_lists_stay_newest_first(self):
        ids = [self.post_job(title=f'Job {i}').id for i in range(3)]
        mine = [v['id'] for v in self.client_c.get(f'{API}mine/').json()['results']]
        self.assertEqual(mine, list(reversed(ids)))
        from jobs.vacancy_service import with_counts
        from jobs.vacancy_models import Vacancy
        self.assertTrue(with_counts(Vacancy.objects.all()).ordered)
