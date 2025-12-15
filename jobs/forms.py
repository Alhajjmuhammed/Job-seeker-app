from django import forms
from .models import JobRequest, JobApplication, Message, DirectHireRequest


class JobRequestForm(forms.ModelForm):
    requirements = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any specific skills, tools, or qualifications needed'
        })
    )
    
    class Meta:
        model = JobRequest
        fields = [
            'title', 'description', 'category', 'location',
            'budget', 'duration_days', 'workers_needed', 'urgency'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of days'}),
            'workers_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10', 'placeholder': 'How many workers do you need?'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
        }


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['cover_letter_file', 'cover_letter', 'proposed_rate']
        widgets = {
            'cover_letter_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Add a brief message or summary...'
            }),
            'proposed_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Your proposed rate'
            }),
        }
        labels = {
            'cover_letter_file': 'Upload Application Letter',
            'cover_letter': 'Additional Notes (Optional)',
            'proposed_rate': 'Proposed Hourly Rate'
        }


class DirectHireRequestForm(forms.ModelForm):
    """Form for clients to request/book a worker directly"""
    
    class Meta:
        model = DirectHireRequest
        fields = [
            'title', 'description', 'location', 
            'duration_type', 'duration_value', 'start_datetime', 
            'offered_rate'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fix kitchen plumbing, Paint bedroom wall'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the work in detail...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Work location address'
            }),
            'duration_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'duration_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'How many hours/days?'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'offered_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Rate per hour/day'
            }),
        }
        labels = {
            'title': 'What work do you need?',
            'description': 'Work Details',
            'location': 'Where is the work?',
            'duration_type': 'Duration Type',
            'duration_value': 'How long?',
            'start_datetime': 'When to start?',
            'offered_rate': 'Your offered rate (SDG)',
        }
    
    def __init__(self, *args, **kwargs):
        worker_hourly_rate = kwargs.pop('worker_hourly_rate', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill rate with worker's hourly rate if available
        if worker_hourly_rate and not self.instance.pk:
            self.fields['offered_rate'].initial = worker_hourly_rate
            self.fields['offered_rate'].help_text = f"Worker's rate: {worker_hourly_rate} SDG/hour"


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type your message...'}),
        }
