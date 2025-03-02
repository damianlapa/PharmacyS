from django.db import models
from django.contrib.auth.models import User

import datetime


SHIFT_TYPES = (
    ('Main', 'Main'),
    ('Secondary', 'Secondary')
)

TITLE_CHOICES = (
    ('Magister', 'Mgr'),
    ('Technik', 'Tech.')
)


class Person(models.Model):
    """
    Model osoby
    user - pole opisujące relację 1 do 1 z użytkownikiem
    name - nazwa osoby
    title - tytuł zawodowy
    """
    user = models.OneToOneField(User, on_delete=models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=32)
    title = models.CharField(max_length=32, choices=TITLE_CHOICES)

    def __str__(self):
        return f'{self.name}'


class Slot(models.Model):
    """
    Przechowuje informację o przypisaniu osoby do odpowieniego dnia
    """
    date = models.DateField()
    person = models.ForeignKey(Person, on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return f'{self.date} | {self.person}'


class Schedule(models.Model):
    """
    Model terminarza
    name - nazwa terminarza
    start_day - pierwszy dzień terminarza
    end_date - data końcowa terminarza

    check_correctness() - sprawdza obecność błędów w terminarzu
    """
    name = models.CharField(max_length=32)
    start_day = models.DateField(blank=True)
    end_date = models.DateField(blank=True)

    def __str__(self):
        return f'{self.name} {self.start_day} - {self.end_date}'

    def check_correctness(self):
        warnings = []
        shifts = Shift.objects.filter(schedule=self)

        day = self.start_day
        days = [day]

        while day != self.end_date:
            day += datetime.timedelta(days=1)
            days.append(day)

        for d in days:
            for s in shifts:
                slots = s.slots.filter(date=d)
                if s.shift_type == 'Main':
                    correct = False
                    for slot in slots:
                        if slot.person:
                            if slot.person.title == 'Magister':
                                correct = True
                    if not correct:
                        warnings.append(f'{d} {s.start_hour} - {s.end_hour} - brak magistra na zmianie')
        return warnings


class Shift(models.Model):
    """
    Model zmiany przechowujący informacje o przynależności do odpowiedniego terminarza, nazwę zmiany, godzinach
    pracy, pojemności[ilości slotów] oraz slotach przypisanych do tej zmiany.
    """
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT, blank=True)
    name = models.CharField(max_length=32)
    shift_type = models.CharField(max_length=16, choices=SHIFT_TYPES, default='Main')
    start_hour = models.TimeField(blank=True, null=True)
    end_hour = models.TimeField(blank=True, null=True)
    capacity = models.IntegerField(default=3)
    slots = models.ManyToManyField(Slot, blank=True)

    def __str__(self):
        return f'{self.start_hour} - {self.end_hour}'
