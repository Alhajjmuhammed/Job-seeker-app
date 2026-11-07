"""
Job posts (vacancies) - the second way to use the platform.

Option 1 (quick service, ServiceRequest) is for "fix one thing". This is for a
company or a household that wants workers for a longer time - a hotel that
needs 5 cleaners, a family that needs a house girl for 6 months.

    poster submits  ->  admin reviews  ->  published  ->  workers apply
    ->  poster (or admin) shortlists and hires  ->  contract runs  ->  ends / renews

All the rules live in jobs/vacancy_service.py so the website and the app
follow exactly the same ones. These are only the tables.
"""
from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from workers.models import Category, WorkerProfile


class Vacancy(models.Model):
    KIND_CHOICES = (
        ('home', _('Home / household')),
        ('business', _('Company / business')),
    )
    DURATION_CHOICES = (
        ('one_off', _('A few days')),
        ('1_month', _('1 month')),
        ('3_months', _('3 months')),
        ('6_months', _('6 months')),
        ('12_months', _('12 months')),
        ('permanent', _('Permanent')),
    )
    # how many days each fixed duration lasts (used for the contract end date)
    DURATION_DAYS = {'one_off': 7, '1_month': 30, '3_months': 91, '6_months': 182, '12_months': 365}
    PAY_PERIOD_CHOICES = (
        ('day', _('per day')),
        ('week', _('per week')),
        ('month', _('per month')),
    )
    WORKER_TYPE_CHOICES = (
        ('any', _('Any worker')),
        ('professional', _('Professional')),
        ('non_academic', _('Non-Academic')),
    )
    STATUS_CHOICES = (
        ('review', _('Under review')),
        ('changes', _('Changes requested')),
        ('published', _('Published')),
        ('rejected', _('Rejected')),
        ('filled', _('Filled')),
        ('closed', _('Closed')),
    )

    poster = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacancies')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='home')
    company_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='vacancies')

    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    worker_type_needed = models.CharField(max_length=15, choices=WORKER_TYPE_CHOICES, default='any')
    workers_needed = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])

    duration = models.CharField(max_length=12, choices=DURATION_CHOICES, default='3_months')
    start_date = models.DateField()
    closing_date = models.DateField(help_text='Last day workers can apply')

    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0)])
    pay_period = models.CharField(max_length=6, choices=PAY_PERIOD_CHOICES, default='month')
    pay_day = models.CharField(max_length=100, blank=True, help_text='e.g. "End of each month"')

    # public: city + area. private: the exact address (only hired workers + admin)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=255, blank=True)

    working_days = models.CharField(max_length=100, blank=True, help_text='e.g. "Monday to Saturday"')
    working_hours = models.CharField(max_length=100, blank=True, help_text='e.g. "7am - 5pm"')

    # household jobs
    live_in = models.BooleanField(default=False)
    food_provided = models.BooleanField(default=False)
    room_provided = models.BooleanField(default=False)
    duties = models.TextField(blank=True)
    trial_period = models.CharField(max_length=100, blank=True, help_text='e.g. "2 weeks"')

    # who the poster is - checked by the admin before publishing
    verification_number = models.CharField(
        max_length=60, blank=True,
        help_text='National ID (NIDA) for a household, TIN or BRELA number for a company')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='review')
    review_note = models.TextField(blank=True, help_text='Reason shown to the poster when rejected / changes asked')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='vacancies_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'closing_date']),
            models.Index(fields=['poster', '-created_at']),
            models.Index(fields=['category', 'city']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    @property
    def poster_display_name(self):
        if self.kind == 'business' and self.company_name:
            return self.company_name
        return self.poster.get_full_name() or 'A household'

    @property
    def hired_count(self):
        """Workers holding a place. A hire whose contract was ended early
        ('ended') gives the place back, so a replacement can be hired.
        Lists annotate hired_n (see vacancy_service.with_counts) to avoid
        one query per row."""
        n = getattr(self, 'hired_n', None)
        return n if n is not None else self.applications.filter(status='hired').count()

    @property
    def applicant_count(self):
        n = getattr(self, 'applicant_n', None)
        return n if n is not None else self.applications.exclude(status='withdrawn').count()

    @property
    def places_left(self):
        return max(self.workers_needed - self.hired_count, 0)

    @property
    def is_open(self):
        """Published, still taking applications, and not every place filled."""
        return (self.status == 'published' and self.closing_date >= timezone.localdate()
                and self.places_left > 0)

    def contract_end_date(self, start):
        days = self.DURATION_DAYS.get(self.duration)
        return start + timedelta(days=days) if days else None


class VacancyApplication(models.Model):
    STATUS_CHOICES = (
        ('applied', _('Applied')),
        ('shortlisted', _('Shortlisted')),
        ('hired', _('Hired')),
        ('not_selected', _('Not selected')),
        ('withdrawn', _('Withdrawn')),
        ('ended', _('Contract ended early')),
    )
    ACTIVE = ('applied', 'shortlisted')

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='vacancy_applications')
    message = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=14, choices=STATUS_CHOICES, default='applied')
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='vacancy_decisions')
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['vacancy', 'worker'], name='one_application_per_worker'),
        ]

    def __str__(self):
        return f'{self.worker} -> {self.vacancy.title} ({self.status})'


class EmploymentContract(models.Model):
    STATUS_CHOICES = (
        ('active', _('Active')),
        ('finished', _('Finished')),
        ('ended_early', _('Ended early')),
        ('renewed', _('Renewed')),
    )
    OPEN = ('active',)

    # one hire can have several contract periods (the first one + renewals)
    application = models.ForeignKey(VacancyApplication, on_delete=models.CASCADE, related_name='contracts')
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='contracts')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='contracts')
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employer_contracts')

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Empty for a permanent job')
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_period = models.CharField(max_length=6, choices=Vacancy.PAY_PERIOD_CHOICES, default='month')
    terms = models.TextField(blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='active')
    end_reason = models.TextField(blank=True)
    ended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='contracts_ended')
    ended_at = models.DateTimeField(null=True, blank=True)
    renewed_from = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='renewal')
    ending_reminder_sent = models.BooleanField(default=False)

    # each side rates the other once the contract is over
    employer_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Employer's rating of the worker")
    employer_feedback = models.TextField(blank=True)
    worker_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Worker's rating of the employer")
    worker_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'end_date'])]

    def __str__(self):
        return f'{self.worker} for {self.employer} ({self.status})'
