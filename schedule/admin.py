from django.contrib import admin
from schedule.models import Person, Slot, Shift, Schedule

admin.site.register(Person)
admin.site.register(Slot)
admin.site.register(Shift)
admin.site.register(Schedule)
