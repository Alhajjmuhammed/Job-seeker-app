"""
Regression tests for the jobs deep scan (bookings, job posts, direct hire, admin):
each test is one bug that was found, reproduced and fixed.

    python manage.py test tests.test_jobs_scan_fixes
"""
from datetime import timedelta
from decimal import Decimal as D

from django.utils import timezone

from jobs.models import Report
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking
from tests.test_full_flows import FlowBase, post_json


class BookingLifecycleFixes(FlowBase):
    def assign(self, sr, wp):
        return post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': wp.id})

    def test_assigning_second_worker_keeps_job_in_progress(self):
        sr, _ = self.book(workers=2)
        self.assign_and_accept(sr)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'in_progress')
        self.assertIn(self.assign(sr, self.wp2).status_code, (200, 201))
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'in_progress')  # used to fall back to "assigned"
        # ...so the client still can't cancel a job that has started
        r = post_json(self.client_c, f'/api/v1/client/service-requests/{sr.id}/cancel/')
        self.assertEqual(r.status_code, 400)

    def test_cancelled_booking_cannot_be_assigned_again(self):
        sr, _ = self.book()
        sr.cancel()
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/reassign/', {'worker_id': self.wp.id})
        self.assertEqual(r.status_code, 400)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'cancelled')
        self.assertFalse(ServiceRequestAssignment.objects.filter(service_request=sr).exists())

    def test_client_finish_releases_workers_still_pending(self):
        sr, _ = self.book(workers=2)
        self.assign_and_accept(sr)
        self.assign(sr, self.wp2)
        r = post_json(self.client_c, f'/api/v1/clients/requests/{sr.id}/complete/')
        self.assertEqual(r.status_code, 200, r.content)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')
        self.assertIsNotNone(sr.work_completed_at)  # counted in revenue now
        pending = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp2)
        self.assertEqual(pending.status, 'cancelled')
        self.wp2.refresh_from_db()
        self.assertEqual(self.wp2.availability, 'available')

    def test_finished_job_is_never_turned_into_cancelled(self):
        sr, _ = self.book()
        sr.status = 'completed'
        sr.save(update_fields=['status'])
        r = post_json(self.admin_c, '/api/v1/admin/bulk/jobs/', {'action': 'close', 'job_ids': [sr.id]})
        self.assertEqual(r.status_code, 200)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')
        self.assertFalse(sr.cancel())

    def test_long_forgotten_clock_out_does_not_crash(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        TimeTracking.objects.create(service_request=sr, worker=self.wp,
                                    clock_in=timezone.now() - timedelta(days=45))
        r = post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/clock-out/')
        self.assertEqual(r.status_code, 200, r.content)  # was a 500 (field held max 999.99 hours)
        log = TimeTracking.objects.get(service_request=sr, worker=self.wp)
        self.assertGreater(log.duration_hours, D('1000'))

    def test_unassign_refuses_a_started_or_finished_job(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        asg.status = 'completed'
        asg.save(update_fields=['status'])
        sr.status = 'completed'
        sr.save(update_fields=['status'])
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/unassign/{asg.id}/')
        self.assertTrue(ServiceRequestAssignment.objects.filter(pk=asg.pk).exists())
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')

    def test_unassign_of_pending_worker_puts_job_back_in_queue(self):
        sr, _ = self.book()
        self.assign(sr, self.wp)
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/unassign/{asg.id}/')
        self.assertFalse(ServiceRequestAssignment.objects.filter(pk=asg.pk).exists())
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'pending')

    def test_bulk_assign_refuses_a_busy_worker(self):
        sr, _ = self.book(workers=2)
        self.wp2.availability = 'busy'
        self.wp2.save(update_fields=['availability'])
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/bulk-assign/',
                      {'worker_ids': [self.wp.id, self.wp2.id]})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(ServiceRequestAssignment.objects.filter(service_request=sr).exists())

    def test_website_cannot_cancel_a_job_in_progress(self):
        sr, _ = self.book()
        self.assign_and_accept(sr)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'in_progress')
        self.client_c.post(f'/services/client/request/{sr.id}/cancel/',
                           {'cancellation_reason_type': 'no_longer_needed', 'cancellation_reason': 'x'})
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'in_progress')


class SavedJobsPrivacy(FlowBase):
    def test_worker_cannot_save_and_read_someone_elses_private_booking(self):
        sr, _ = self.book()
        sr.status = 'completed'
        sr.save(update_fields=['status'])
        r = self.worker_c.post(f'/api/v1/job-completion/{sr.id}/save/')
        self.assertEqual(r.status_code, 404)
        r = self.worker_c.get('/api/v1/job-completion/saved/?include_closed=true')
        self.assertNotIn('12 Secret Street', r.content.decode())


class AdminAndApiInputFixes(FlowBase):
    def test_dismiss_without_ban_does_not_ban(self):
        report = Report.objects.create(reporter=self.client_user, reported_user=self.worker_user,
                                       content_type='user', content_id=self.worker_user.id, report_type='spam')
        r = self.admin_c.post(f'/api/messages/reports/{report.id}/review/',
                              {'status': 'dismissed', 'ban_user': 'false'})
        self.assertEqual(r.status_code, 200, r.content)
        self.worker_user.refresh_from_db()
        self.assertTrue(self.worker_user.is_active)

    def test_staff_cannot_be_banned_from_a_report(self):
        report = Report.objects.create(reporter=self.client_user, reported_user=self.admin,
                                       content_type='user', content_id=self.admin.id, report_type='spam')
        r = self.admin_c.post(f'/api/messages/reports/{report.id}/review/', {'status': 'resolved', 'ban_user': 'true'})
        self.assertEqual(r.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_bad_numbers_in_links_are_not_500s(self):
        for c, url in ((self.admin_c, '/dashboard/jobs/?category=abc'),
                       (self.admin_c, '/dashboard/service-requests/?category=abc'),
                       (self.client_c, '/api/v1/job-categories/popular/?limit=abc'),
                       (self.client_c, '/api/v1/job-categories/popular/?limit=-1'),
                       (self.admin_c, '/api/messages/reports/list/?page=abc')):
            self.assertLess(c.get(url).status_code, 500, url)
        r = post_json(self.client_c, '/api/messages/send/', {'recipient_id': 'abc', 'message': 'hi'})
        self.assertLess(r.status_code, 500)
        r = post_json(self.client_c, '/api/messages/reports/',
                      {'content_type': 'user', 'content_id': 'abc', 'report_type': 'spam'})
        self.assertEqual(r.status_code, 400)

    def test_category_rename_to_existing_name_is_a_clear_error(self):
        from workers.models import Category
        other = Category.objects.create(name='Electrician')
        r = self.admin_c.put(f'/api/v1/job-categories/{other.id}/update/', '{"name": "plumber"}',
                             content_type='application/json')
        self.assertEqual(r.status_code, 400, r.content)

    def test_direct_hire_answer_as_a_client_is_not_a_500(self):
        r = post_json(self.client_c, '/api/jobs/worker/direct-hire-requests/1/accept/')
        self.assertLess(r.status_code, 500)


class ShortStaffedBookings(FlowBase):
    """Paid for 2 workers, only 1 finished: admin decides (no silent close)."""

    def test_short_staffed_job_waits_for_admin_and_can_be_closed(self):
        from worker_connect.notification_models import Notification
        sr, _ = self.book(workers=2)
        asg = self.assign_and_accept(sr)
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp2.id})
        a2 = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp2)
        self.assertTrue(a2.reject_assignment('cannot come'))
        asg.mark_completed()
        sr.refresh_from_db()
        self.assertNotEqual(sr.status, 'completed')  # used to close silently
        self.assertEqual(sr.short_staffed(), (1, 2))
        self.assertTrue(Notification.objects.filter(recipient=self.admin, title='Booking needs a decision').exists())
        page = self.admin_c.get(f'/dashboard/service-requests/{sr.id}/').content.decode()
        self.assertIn('Close as done', page)
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/close-done/')
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')

    def test_full_team_still_closes_by_itself(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        asg.mark_completed()
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')


class DirectHireCancel(FlowBase):
    def make_hire(self, status='pending'):
        from jobs.models import DirectHireRequest
        return DirectHireRequest.objects.create(
            client=self.client_user, worker=self.wp, title='Paint room', description='x', location='Dar',
            duration_type='days', duration_value=2, start_datetime=timezone.now() + timedelta(days=1),
            offered_rate=D('20000'), status=status)

    def test_client_cancels_accepted_booking_and_worker_is_freed(self):
        hire = self.make_hire('accepted')
        self.wp.availability = 'busy'
        self.wp.save(update_fields=['availability'])
        r = post_json(self.client_c, f'/api/jobs/direct-hire-requests/{hire.id}/cancel/', {'reason': 'changed plans'})
        self.assertEqual(r.status_code, 200, r.content)
        hire.refresh_from_db()
        self.wp.refresh_from_db()
        self.assertEqual(hire.status, 'cancelled')
        self.assertEqual(self.wp.availability, 'available')
        from jobs.chat_access import can_chat
        self.assertFalse(can_chat(self.client_user, self.worker_user))

    def test_worker_cancels_only_after_accepting_and_outsiders_cannot(self):
        hire = self.make_hire('pending')
        self.assertEqual(post_json(self.worker_c, f'/api/jobs/direct-hire-requests/{hire.id}/cancel/').status_code, 400)
        hire.status = 'accepted'
        hire.save(update_fields=['status'])
        other = self.client_class()
        other.force_login(self.other_client)
        self.assertEqual(post_json(other, f'/api/jobs/direct-hire-requests/{hire.id}/cancel/').status_code, 404)
        self.worker_c.post(f'/jobs/direct-hire/{hire.id}/cancel/', {'reason': 'sick'})
        hire.refresh_from_db()
        self.assertEqual(hire.status, 'cancelled')

    def test_complete_with_bad_rating_is_not_a_500(self):
        hire = self.make_hire('accepted')
        r = self.client_c.post(f'/jobs/direct-hire/{hire.id}/complete/', {'rating': 'abc'})
        self.assertLess(r.status_code, 500)
        hire.refresh_from_db()
        self.assertEqual(hire.status, 'completed')
        self.assertIsNone(hire.client_rating)


class TanzaniaTime(FlowBase):
    def test_today_is_tanzania_today(self):
        from django.conf import settings
        self.assertEqual(settings.TIME_ZONE, 'Africa/Dar_es_Salaam')
        from unittest import mock
        from datetime import datetime, timezone as dtz
        late_utc = datetime(2026, 11, 8, 22, 30, tzinfo=dtz.utc)  # 01:30 on the 9th in Dar
        with mock.patch('django.utils.timezone.now', return_value=late_utc):
            self.assertEqual(str(timezone.localdate()), '2026-11-09')
