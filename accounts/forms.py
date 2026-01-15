from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'placeholder': 'Enter 10-digit mobile number',
            'inputmode': 'numeric',
            'pattern': '\\d{10}',
            'maxlength': '10'
        })
    )
    sms_opt_in = forms.BooleanField(required=False, initial=True, label='Receive SMS notifications')
    admin_code = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Enter admin security code (optional)',
        'type': 'password'
    }))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'sms_opt_in', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Enter username'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter email'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError('Enter a valid 10-digit mobile number')
        return digits