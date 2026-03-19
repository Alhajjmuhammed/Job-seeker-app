from django import forms
from accounts.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import AgentProfile


class AgentRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    first_name = forms.CharField(
        required=True, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        required=True, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    phone_number = forms.CharField(
        required=True, max_length=17,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255...'})
    )
    business_name = forms.CharField(
        required=False, max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business or trading name (optional)'}),
        help_text="Leave blank to use your full name"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'agent'
        if commit:
            user.save()
            AgentProfile.objects.create(
                user=user,
                business_name=self.cleaned_data.get('business_name', '')
            )
        return user


class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = AgentProfile
        fields = ['business_name', 'bio']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class AgentCreateWorkerForm(UserCreationForm):
    """Form used by an agent to create a new worker account directly."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    first_name = forms.CharField(
        required=True, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        required=True, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    phone_number = forms.CharField(
        required=True, max_length=17,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255...'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Set a password for the worker'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'worker'
        if commit:
            user.save()
        return user
