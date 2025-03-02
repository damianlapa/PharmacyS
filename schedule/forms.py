from django import forms
from schedule.models import Schedule, Person, TITLE_CHOICES, Shift
from django.contrib.auth.models import Group, User


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = '__all__'

        widgets = {
            'start_day': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
            'end_date': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
        }


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = '__all__'


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'password', 'groups')

        widgets = {
            'password': forms.PasswordInput()
        }


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ('schedule', 'name', 'shift_type', 'start_hour', 'end_hour', 'capacity')

        widgets = {
            'start_hour': forms.TimeInput(attrs={'type': 'time'}, format="%H:%M"),
            'end_hour': forms.TimeInput(attrs={'type': 'time'}, format="%H:%M")
        }

class UserPersonForm(forms.Form):
    """groups = Group.objects.all()

    group_choices = []

    for g in groups:
        group_choices.append((g.id, g.name))"""

    username = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    name = forms.CharField(required=True)
    title = forms.ChoiceField(choices=TITLE_CHOICES)
    group = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)
