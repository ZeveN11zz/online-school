from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError
from django.forms import ModelForm, widgets, fields, Form
from django.forms.utils import ErrorList

from shop.models import Dispute


class RegisterForm(ModelForm):
    password1 = fields.CharField(widget=widgets.PasswordInput(), max_length=20, min_length=8, label='Пароль')
    password2 = fields.CharField(widget=widgets.PasswordInput(), max_length=20, min_length=8,
                                 label='Подтверждение пароля')

    def is_valid(self):
        if self.data['password1'] != self.data['password2']:
            self.add_error('password2', 'Пароли не совпадают')
            return False
        return super().is_valid()

    def save(self, commit=True):
        self.instance.username = self.cleaned_data['email']
        self.instance.set_password(self.cleaned_data['password1'])
        try:
            return super().save(commit)
        except IntegrityError:
            self.add_error('email', 'Пользователь с таким email уже зарегистрирован.')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']


class DisputeForm(ModelForm):
    class Meta:
        model = Dispute
        fields = ['dispute_text']
