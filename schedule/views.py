from django.shortcuts import render, HttpResponse, redirect
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from schedule.models import Schedule, Shift, Slot, Person
from schedule.forms import ScheduleForm, PersonForm, GroupForm, UserForm, UserPersonForm, ShiftForm
from django.contrib.auth import authenticate, login, logout, models
from django.template.loader import get_template

import datetime
from xhtml2pdf import pisa

DAYS = ('pn', 'wt', 'śr', 'cz', 'pt', 'sb', 'nd')


class IndexView(LoginRequiredMixin, View):
    """
    Widok wyświetlający stronę główną dla zalogowanych użytkowników.
    Jeśli użytkownik nie jest zalogowany zostanie przekierowany na strone logowania.
    """
    login_url = 'login'

    def get(self, request):
        return render(request, 'schedule/index.html', locals())


class LoginView(View):
    """
    Widok logowania.

    Metoda GET wyświetla formularz logowania jeśli użytkownik nie jest zalogowany. W przeciwnym wypadku przekierowuje
    na stronę główną.
    Metoda POST sprawdza poprawność danych logowania. Jesli dane są prawidłowe, użytkownik zostanie przekierowany na
    stronę główną. Jeśli dane są nieprawidłowe wyświetli ponownie widok logowania metodą GET.
    """
    def get(self, request):
        user = request.user
        if user.is_authenticated:
            return redirect('index')
        else:
            return render(request, 'schedule/login.html', locals())

    def post(self, request):
        login_ = request.POST.get('login')
        password = request.POST.get('password')

        user = authenticate(username=login_, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            message = 'Użytkownik nie istnieje'
            return render(request, 'schedule/login.html', locals())


class LogoutView(View):
    """
    Wylogowywanie użytkownika. Po wylogowaniu użytkownik zostanie przeniesiony na stronę logowania.
    """
    def get(self, request):
        logout(request)
        return redirect('login')


class ScheduleAdd(PermissionRequiredMixin, View):
    """
    Dodawanie terminarza.
    Jeśli użytkonik jest zalogowany i posiada uprawnienie do dodawania terminarza to po wejściu:
    Metodą GET - zostanie wyświetlony formularz do dodania nowego terminarza.
    Metodą POST - po sprawdzeniu poprawności zostanie dodany nowy terminarz.
    Jesli użytkownik nie posiada odpowiednich uprawnień zostanie wyświetlony komunikat o braku uprawnień
    """
    permission_required = 'schedule.add_schedule'

    def get(self, request):
        form = ScheduleForm
        return render(request, 'schedule/schedule-add.html', locals())

    def post(self, request):
        form = ScheduleForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            name = data['name']
            start_day = data['start_day']
            end_date = data['end_date']

            schedule = Schedule.objects.create(name=name, start_day=start_day, end_date=end_date)

            Shift.objects.create(schedule=schedule, name='Pierwsza Zmiana', shift_type='Main',
                                 start_hour=datetime.datetime.strptime('08:00', '%H:%M'),
                                 end_hour=datetime.datetime.strptime('16:00', '%H:%M'), capacity=3)

            return redirect('schedule-list')
        else:
            return redirect('schedule-list')

class ScheduleListView(PermissionRequiredMixin, View):
    """
    Wyświetlanie terminarzy.
    Jeśli użytkonik jest zalogowany i posiada uprawnienie do obejrzenia terminarzy to po wejściu:
    Metodą GET - zostanie wyświetlona lista terminarzy. W przypadku posiadania dodatkowych uprawnień użytkownik
    będzie widział dodatkowe opcje edycji oraz sprawdzenia poprawności terminarza.
    Jesli użytkownik nie posiada odpowiednich uprawnień zostanie wyświetlony komunikat o braku uprawnień
    """
    permission_required = 'schedule.view_schedule'

    def get(self, request):
        schedules = Schedule.objects.all()
        return render(request, 'schedule/schedule-list.html', locals())


class ScheduleDetailView(PermissionRequiredMixin, View):
    """
    Szczegółwy widok terminarza.

    Metoda GET - niezbędne będzie przekazanie id terminarza, który ma zostać wyświetlony.
    Widok generuje tabelę obrazująca terminarz.
    """
    permission_required = 'schedule.view_schedule'

    def get(self, request, schedule_id):
        schedule = Schedule.objects.get(id=schedule_id)
        shifts = Shift.objects.filter(schedule=schedule).order_by('start_hour')

        temp_shifts = []
        main_shifts = []

        for s in shifts:
            if s.shift_type == 'Main':
                main_shifts.append(s)
            else:
                temp_shifts.append(s)

        for num in range(len(main_shifts)):
            if num == 0:
                temp_shifts.insert(num, main_shifts[num])
            else:
                temp_shifts.append(main_shifts[num])

        shifts = temp_shifts

        data = []

        day = schedule.start_day
        days = [day]

        while day != schedule.end_date:
            day += datetime.timedelta(days=1)
            days.append(day)

        for d in days:
            for s in shifts:
                slot_num = 0
                for slot_shift in s.slots.all():
                    if slot_shift.date == d:
                        slot_num += 1
                while slot_num < s.capacity:
                    slot = Slot.objects.create(date=d)
                    s.slots.add(slot)
                    slot_num += 1

        for d in days:
            str_day = datetime.datetime.strftime(d, '%d')
            if str_day[0] == '0':
                str_day = str_day[1:]
            row = [str_day, DAYS[datetime.datetime.isoweekday(d) - 1]]
            for s in shifts:
                for slot in s.slots.all():
                    if slot.date == d:
                        row.append(slot.person) if slot.person else row.append('-------')
            data.append(row)

        return render(request, 'schedule/schedule-view.html', locals())


class ScheduleEditView(PermissionRequiredMixin, View):
    """
    Edycja terminarza
    Po wejściu metodą GET: zostanie wyświetlony terminarz z opcją edycji poszczególnych slotów w terminarzu.
    W widoku zostaną udostepnione również przyciski do edycji zmian pracowników w terminarzu(dodawanie oraz usuwanie)
    Dostępne będzie również usunięcie terminarza.

    Po wejściu metodą POST zostaną zapisane zmiany w terminarzu.
    """
    permission_required = 'schedule.change_schedule'

    def get(self, request, schedule_id):
        persons = Person.objects.filter(user__isnull=False)
        schedule = Schedule.objects.get(id=schedule_id)
        shifts = Shift.objects.filter(schedule=schedule).order_by('start_hour')

        temp_shifts = []
        main_shifts = []

        for s in shifts:
            if s.shift_type == 'Main':
                if len(temp_shifts) == 0:
                    temp_shifts.insert(0, s)
                else:
                    main_shifts.append(s)
            else:
                temp_shifts.append(s)

        for s in main_shifts:
            temp_shifts.append(s)

        shifts = temp_shifts

        shifts_data = []

        day = schedule.start_day
        days = [day]

        while day != schedule.end_date:
            day += datetime.timedelta(days=1)
            days.append(day)

        for d in days:
            str_day = datetime.datetime.strftime(d, '%d')
            if str_day[0] == '0':
                str_day = str_day[1:]
            row = [str_day, DAYS[datetime.datetime.isoweekday(d) - 1]]
            for shift in shifts:
                for slot in shift.slots.all().filter(date=d).order_by('id'):
                    row.append(slot)
            shifts_data.append(row)

        return render(request, 'schedule/schedule-edit.html', locals())

    def post(self, request, schedule_id):
        schedule = Schedule.objects.get(id=schedule_id)
        shifts = Shift.objects.filter(schedule=schedule).order_by('start_hour')

        for shift in shifts:
            for slot in shift.slots.all():
                slot_data = request.POST.get(f'slot_id{slot.id}')
                if slot_data != '---':
                    slot.person = Person.objects.get(id=int(slot_data))
                else:
                    if slot.person:
                        slot.person = None
                slot.save()

        return redirect('schedule-detail', schedule_id=schedule.id)


class ScheduleCheckoutView(PermissionRequiredMixin, View):
    """
    Sprawdzenie poprawności stworzonego terminarza
    Po wejściu metodą GET zostaną wyświetlone informacje na temat ewentualnych ostrzeżeń dotyczących danego
    terminarza.
    """
    permission_required = 'schedule.change_schedule'

    def get(self, request, schedule_id):
        schedule = Schedule.objects.get(id=schedule_id)
        warrnings = schedule.check_correctness()

        return render(request, 'schedule/schedule-checkout.html', locals())


class PersonAdd(PermissionRequiredMixin, View):
    """
    Dodawanie osób.
    Po wejściu metodą GET zostanie wyświetlony formularz do stworzenia nowej osoby.
    Po wejściu metodą POST i sprawdzeniu poprawności danych zostanie utworzona nowa osoba.
    Jeśli dane będą niepoprawne wraca na widok metodą GET z informacją o błędach.
    """
    permission_required = 'schedule.add_person'

    def get(self, request):
        form = UserPersonForm
        return render(request, 'schedule/person-add.html', locals())

    def post(self, request):
        form = UserPersonForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            username = data['username']
            password = data['password']
            groups = data['group']

            user = models.User.objects.create_user(username, password=password)

            for g in groups:
                user.groups.add(g)

            name = data['name']
            title = data['title']

            person = Person.objects.create(user=user, name=name, title=title)
            return redirect('person-all')
        else:
            # errors = form.errors
            return render(request, 'schedule/person-add.html', locals())


class PersonListView(PermissionRequiredMixin, View):
    """
    Widok po wejściu metodą GET wyświetla listę osób jeśli użytkownik posiada odpowiednie uprawnienia. W przeciwnym
    wypadku zostanie wyświetlony komunikat o braku uprawnień.
    """
    permission_required = 'schedule.add_person'

    def get(self, request):
        persons = Person.objects.all()

        return render(request, 'schedule/person-all.html', locals())


class GroupAdd(PermissionRequiredMixin, View):
    """
    Dodawanie grup z przypisanymi im uprawnieniami.
    Po wejściu:
    - metodą GET: zostanie wyświetlony formularz dodawania nowej grupy
    - metodą POST: zostanie utworzona nowa grupa wraz z uprawnieniami
    """
    permission_required = 'authentication.add_group'

    def get(self, request):
        form = GroupForm
        return render(request, 'schedule/group-add.html', locals())

    def post(self, request):
        form = GroupForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data['name']
            permissions = form.cleaned_data['permissions']

            group = models.Group.objects.create(name=name)

            for p in permissions:
                group.permissions.add(p)

            return redirect('index')


class GroupListView(PermissionRequiredMixin, View):
    """
    Wyświetlanie grup
    Metoda GET: wyświetla listę grup
    """
    permission_required = 'authenticate.add_group'

    def get(self, request):
        groups = models.Group.objects.all()

        return render(request, 'schedule/group-all.html', locals())


class UserAdd(PermissionRequiredMixin, View):
    """
    Dodawanie użytkowników.
    Po wejściu metodą GET zostanie wyświetlony formularz do stworzenia nowego użytkownika.
    Po wejściu metodą POST i sprawdzeniu poprawności danych zostanie utworzony nowy użytkownik.
    """
    permission_required = 'authentication.add_user'

    def get(self, request):
        form = UserForm
        return render(request, 'schedule/user-add.html', locals())

    def post(self, request):
        form = UserForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            user = models.User.objects.create_user(username=data['username'], password=data['password'])


class ShiftAddView(PermissionRequiredMixin, View):
    """
    Dodawanie zmian
    Metoda GET: wyświetlenie formularza do dodawania zmian. Jeśli przekażemy id terminarza zostanie on domyślnie
    wybrany w formularzu
    Metoda POST: dodanie zmiany oraz przeniesienie na widok terminarza, do którego została dodana zmiana
    """
    permission_required = 'schedule.add_shift'

    def get(self, request):
        schedule = None
        if request.GET.get('schedule_id'):
            schedule_id = request.GET.get('schedule_id')
            schedule = Schedule.objects.get(id=int(schedule_id))
        form = ShiftForm if not schedule else ShiftForm(initial={'schedule': schedule})
        return render(request, 'schedule/shift-add.html', locals())

    def post(self, request):
        form = ShiftForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            schedule = data['schedule']
            name = data['name']
            shift_type = data['shift_type']
            start_hour = data['start_hour']
            end_hour = data['end_hour']
            capacity = data['capacity']

            shift = Shift.objects.create(schedule=schedule, name=name, shift_type=shift_type, start_hour=start_hour,
                                         end_hour=end_hour, capacity=capacity)

            return redirect('schedule-detail', schedule_id=schedule.id)
        else:
            return redirect('shift-add')

class ShiftDeleteView(PermissionRequiredMixin, View):
    """
    Usuwanie zmian

    Jesli użytkownik posiada uprawnienie do usuwania zmian, widok usunie zmianą o przekazanym id zmiany[shift_id].
    Następnie następi przekierowanie do szczegółowego widoku terminarza, do którego zmiana była przypisana.
    """
    permission_required = 'schedule.delete_shift'

    def get(self, request, shift_id):
        shift = Shift.objects.get(id=shift_id)
        schedule_id = shift.schedule.id
        slots = Slot.objects.filter(shift=shift)
        for s in slots:
            s.delete()
        shift.delete()
        return redirect('schedule-detail', schedule_id=schedule_id)


class ScheduleDeleteView(PermissionRequiredMixin, View):
    """
    Usuwanie terminarza
    Po wejściu metodą GET, jesli użytkownik posiada odpowiednie uprawnienie nastąpi usunięcie terminarza.
    """
    permission_required = 'schedule.schedule_delete'

    def get(self, request, schedule_id):
        schedule = Schedule.objects.get(id=schedule_id)
        shifts = Shift.objects.filter(schedule=schedule)
        for s in shifts:
            s.delete()
        schedule.delete()
        return redirect('index')


class UserDeleteView(PermissionRequiredMixin, View):
    permission_required = 'authentication.user_delete'

    def get(self, request, user_id):
        user = models.User.objects.get(id=user_id)
        person = Person.objects.filter(user=user)

        if person:
            person[0].user = None
            person[0].save()

        if user != request.user:
            user.delete()

        return redirect('index')


class PersonEditView(PermissionRequiredMixin, View):
    permission_required = 'schedule.change_person'

    def get(self, request, person_id):
        person = Person.objects.get(id=person_id)
        form = PersonForm(instance=person)

        return render(request, 'schedule/person-edit.html', locals())

    def post(self, request, person_id):
        person = Person.objects.get(id=person_id)
        form = PersonForm(request.POST)

        if form.is_valid():
            person.user = form.cleaned_data['user']
            person.name = form.cleaned_data['name']
            person.title = form.cleaned_data['title']

            person.save()

            return redirect('person-all')


class PrintPDFView(View):

    def get(self, request, schedule_id):
        schedule = Schedule.objects.get(id=schedule_id)
        font_url = "https://fonts.googleapis.com/css?family=Open+Sans:300,700"
        # <----------
        schedule = Schedule.objects.get(id=schedule_id)
        shifts = Shift.objects.filter(schedule=schedule).order_by('start_hour')

        temp_shifts = []
        main_shifts = []

        for s in shifts:
            if s.shift_type == 'Main':
                main_shifts.append(s)
            else:
                temp_shifts.append(s)

        for num in range(len(main_shifts)):
            if num == 0:
                temp_shifts.insert(num, main_shifts[num])
            else:
                temp_shifts.append(main_shifts[num])

        shifts = temp_shifts

        data = []

        day = schedule.start_day
        days = [day]

        while day != schedule.end_date:
            day += datetime.timedelta(days=1)
            days.append(day)

        for d in days:
            for s in shifts:
                slot_num = 0
                for slot_shift in s.slots.all():
                    if slot_shift.date == d:
                        slot_num += 1
                while slot_num < s.capacity:
                    slot = Slot.objects.create(date=d)
                    s.slots.add(slot)
                    slot_num += 1

        for d in days:
            str_day = datetime.datetime.strftime(d, '%d')
            if str_day[0] == '0':
                str_day = str_day[1:]
            row = [str_day, DAYS[datetime.datetime.isoweekday(d) - 1]]
            for s in shifts:
                for slot in s.slots.all():
                    if slot.date == d:
                        row.append(slot.person) if slot.person else row.append('-------')
            data.append(row)
        # ------------>
        html = None
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="report.pdf"'
        template_path = 'schedule/print.html'
        context = locals()
        template = get_template(template_path)
        if not html:
            html = template.render(context)
        else:
            html = html + template.render(context)

        pisa_status = pisa.CreatePDF(
            html, dest=response, encoding='UTF-8')
        # if error
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
