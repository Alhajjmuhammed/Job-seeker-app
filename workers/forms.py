from django import forms
from workers.models import (WorkerProfile, WorkerDocument, WorkExperience, Category, Skill,
                     WorkerCustomSkill, WorkerCustomCategory)


EAST_AFRICAN_COUNTRIES = [
    ('', 'Select Country'),
    ('Tanzania', 'Tanzania'),
    ('Kenya', 'Kenya'),
    ('Uganda', 'Uganda'),
    ('Rwanda', 'Rwanda'),
    ('Burundi', 'Burundi'),
    ('South Sudan', 'South Sudan'),
    ('Somalia', 'Somalia'),
    ('Ethiopia', 'Ethiopia'),
    ('Djibouti', 'Djibouti'),
    ('Eritrea', 'Eritrea'),
]


class WorkerProfileForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=EAST_AFRICAN_COUNTRIES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = WorkerProfile
        fields = [
            'bio', 'address', 'city', 'state', 'country', 'postal_code',
            'religion', 'can_work_everywhere',
            'categories', 'experience_years', 'hourly_rate', 'availability'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'religion': forms.Select(attrs={'class': 'form-select'}),
            'can_work_everywhere': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'categories': forms.CheckboxSelectMultiple(),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'availability': forms.Select(attrs={'class': 'form-select'}),
        }


class ProfileImageForm(forms.ModelForm):
    """Separate form for profile image upload"""
    class Meta:
        model = WorkerProfile
        fields = ['profile_image']
        widgets = {
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make profile_image not required so we can save without it
        self.fields['profile_image'].required = False


class CustomSkillForm(forms.ModelForm):
    class Meta:
        model = WorkerCustomSkill
        fields = ['name', 'description', 'certificate', 'years_of_experience']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., "Solar Panel Installation"'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of your expertise...'
            }),
            'certificate': forms.FileInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Years'
            }),
        }


class CustomCategoryForm(forms.ModelForm):
    class Meta:
        model = WorkerCustomCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., "Drone Photography"'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'What services do you offer in this category?'
            }),
        }



class WorkerDocumentForm(forms.ModelForm):
    class Meta:
        model = WorkerDocument
        fields = ['document_type', 'title', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class WorkExperienceForm(forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ['job_title', 'company', 'location', 'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
