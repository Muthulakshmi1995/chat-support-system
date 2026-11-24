from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Ticket, Message

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("subject", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("content",)
        widgets = {"content": forms.Textarea(attrs={"rows": 3, "placeholder": "Write your message..."})}

class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("status",)
