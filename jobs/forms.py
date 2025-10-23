from django import forms
from .models import JobRequest, JobApplication, Message


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


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type your message...'}),
        }
