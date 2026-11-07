"""Forms for job posts. The app API feeds request.data through the same
VacancyForm, so the website and the app validate a job post identically."""
from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from workers.models import Category

from .models import Report
from .vacancy_models import Vacancy

DATE = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = [
            'kind', 'company_name', 'category', 'title', 'description', 'requirements',
            'worker_type_needed', 'workers_needed', 'duration', 'start_date', 'closing_date',
            'salary_amount', 'salary_max', 'pay_period', 'pay_day',
            'city', 'area', 'address', 'working_days', 'working_hours',
            'live_in', 'food_provided', 'room_provided', 'duties', 'trial_period',
            'verification_number',
        ]
        widgets = {
            'start_date': DATE,
            'closing_date': DATE,
            'description': forms.Textarea(attrs={'rows': 4}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
            'duties': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'kind': _('Who is hiring?'),
            'company_name': _('Company name'),
            'category': _('Type of work'),
            'title': _('Job title'),
            'description': _('Describe the job'),
            'requirements': _('Requirements (experience, certificates, languages...)'),
            'worker_type_needed': _('Worker type'),
            'workers_needed': _('How many workers?'),
            'duration': _('How long?'),
            'start_date': _('Start date'),
            'closing_date': _('Applications close on'),
            'salary_amount': _('Salary (TSh)'),
            'salary_max': _('Up to (optional)'),
            'pay_period': _('Paid'),
            'pay_day': _('Pay day'),
            'city': _('City'),
            'area': _('Area / neighbourhood'),
            'address': _('Exact address (shown only to the workers you hire)'),
            'working_days': _('Working days'),
            'working_hours': _('Working hours'),
            'live_in': _('The worker lives in the house'),
            'food_provided': _('Food provided'),
            'room_provided': _('Room provided'),
            'duties': _('Duties (cooking, cleaning, childcare...)'),
            'trial_period': _('Trial period'),
            'verification_number': _('National ID (NIDA), or TIN / BRELA number for a company'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('name')
        self.fields['category'].required = True
        self.fields['verification_number'].required = True
        # choices with a sensible default: leaving them out (the app may) uses the default
        for name in self.DEFAULTS:
            self.fields[name].required = False
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')

    DEFAULTS = {'kind': 'home', 'worker_type_needed': 'any', 'duration': '3_months',
                'pay_period': 'month', 'workers_needed': 1}

    def clean(self):
        data = super().clean()
        for name, default in self.DEFAULTS.items():
            if name not in self.errors and data.get(name) in (None, ''):
                data[name] = default
        today = timezone.localdate()
        start, closing = data.get('start_date'), data.get('closing_date')
        if closing and closing < today:
            self.add_error('closing_date', _('The closing date cannot be in the past.'))
        if start and start < today:
            self.add_error('start_date', _('The start date cannot be in the past.'))
        if closing and closing > today + timedelta(days=90):
            self.add_error('closing_date', _('Applications can stay open for at most 90 days.'))
        low, high = data.get('salary_amount'), data.get('salary_max')
        if low is not None and high is not None and high < low:
            self.add_error('salary_max', _('"Up to" must be more than the salary.'))
        if data.get('kind') == 'business' and not (data.get('company_name') or '').strip():
            self.add_error('company_name', _('Please enter the company name.'))
        if data.get('kind') != 'home':
            # household-only details make no sense for a company job
            for f in ('live_in', 'food_provided', 'room_provided'):
                data[f] = False
        return data


class ApplyForm(forms.Form):
    message = forms.CharField(
        label=_('Message to the employer (optional)'), required=False, max_length=2000,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


class ReviewForm(forms.Form):
    ACTIONS = (('publish', _('Publish')), ('changes', _('Ask for changes')), ('reject', _('Reject')))
    action = forms.ChoiceField(choices=ACTIONS)
    note = forms.CharField(required=False, max_length=2000,
                           widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))

    def clean(self):
        data = super().clean()
        if data.get('action') in ('changes', 'reject') and not (data.get('note') or '').strip():
            self.add_error('note', _('Tell the poster why.'))
        return data


class HireForm(forms.Form):
    start_date = forms.DateField(label=_('Start date'), required=False, widget=DATE)
    terms = forms.CharField(label=_('Agreed terms (optional)'), required=False, max_length=4000,
                            widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


class EndContractForm(forms.Form):
    reason = forms.CharField(label=_('Reason'), max_length=2000,
                             widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


class RenewForm(forms.Form):
    duration = forms.ChoiceField(label=_('Renew for'), choices=[c for c in Vacancy.DURATION_CHOICES
                                                                 if c[0] != 'one_off'],
                                 widget=forms.Select(attrs={'class': 'form-select'}))


class RateForm(forms.Form):
    rating = forms.IntegerField(label=_('Rating'), min_value=1, max_value=5)
    feedback = forms.CharField(label=_('Feedback (optional)'), required=False, max_length=2000,
                               widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


class ReportForm(forms.Form):
    report_type = forms.ChoiceField(label=_('What is wrong?'), choices=Report.REPORT_TYPE_CHOICES,
                                    widget=forms.Select(attrs={'class': 'form-select'}))
    description = forms.CharField(label=_('Tell us more'), max_length=2000,
                                  widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


__all__ = ['VacancyForm', 'ApplyForm', 'ReviewForm', 'HireForm', 'EndContractForm', 'RenewForm',
           'RateForm', 'ReportForm']
