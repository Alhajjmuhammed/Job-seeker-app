from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class WorkerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    phone_number = forms.CharField(required=True, max_length=17)
    agent_code = forms.CharField(
        required=False, max_length=10,
        help_text="Optional: Enter the agent code if you were referred by an agent.",
        widget=forms.TextInput(attrs={'placeholder': 'Agent code (optional)', 'style': 'text-transform:uppercase'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def clean_agent_code(self):
        code = self.cleaned_data.get('agent_code', '').strip().upper()
        if code:
            from agents.models import AgentProfile
            try:
                AgentProfile.objects.get(agent_code=code, is_verified=True)
            except AgentProfile.DoesNotExist:
                raise forms.ValidationError("Invalid or unrecognised agent code.")
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'worker'
        if commit:
            user.save()
            # Link worker to agent if a valid code was entered
            agent_code = self.cleaned_data.get('agent_code', '').strip().upper()
            from workers.models import WorkerProfile
            profile, _ = WorkerProfile.objects.get_or_create(user=user)
            if agent_code:
                from agents.models import AgentProfile
                try:
                    agent = AgentProfile.objects.get(agent_code=agent_code, is_verified=True)
                    profile.agent = agent
                    profile.save()
                except AgentProfile.DoesNotExist:
                    pass  # code was valid at clean() time but no longer — skip silently
        return user


class ClientRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    phone_number = forms.CharField(required=True, max_length=17)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'client'
        if commit:
            user.save()
        return user


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username or Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset via email"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )


class PasswordResetConfirmForm(forms.Form):
    """Form for setting new password after clicking reset link"""
    password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        min_length=8
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class ChangePasswordForm(forms.Form):
    """Form for changing password when user is logged in"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        min_length=8
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        current_password = cleaned_data.get('current_password')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("New passwords do not match.")
            
            if current_password and new_password1 == current_password:
                raise forms.ValidationError("New password must be different from current password.")
        
        return cleaned_data
