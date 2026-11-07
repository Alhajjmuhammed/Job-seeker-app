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
    ('Tanzania', 'Tanzania'),
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
            'latitude', 'longitude',
            'religion', 'can_work_everywhere',
            'categories', 'experience_years', 'availability', 'worker_type'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
            'religion': forms.Select(attrs={'class': 'form-select'}),
            'can_work_everywhere': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'categories': forms.CheckboxSelectMultiple(),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability': forms.Select(attrs={'class': 'form-select'}),
            'worker_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Switched-off trades are not offered, but a worker keeps the ones
        # they already have (so saving the form does not drop them).
        from django.db.models import Q
        mine = list(self.instance.categories.values_list('pk', flat=True)) if self.instance.pk else []
        self.fields['categories'].queryset = Category.objects.filter(
            Q(is_active=True) | Q(pk__in=mine)).order_by('name')
        # The first-time setup page does not show the type: keep what the
        # worker chose at sign-up instead of failing or blanking it.
        self.fields['worker_type'].required = False

    def clean_worker_type(self):
        return self.cleaned_data.get('worker_type') or self.instance.worker_type or 'non_academic'


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
