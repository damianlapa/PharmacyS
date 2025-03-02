from django.urls import path
from schedule.views import ScheduleDetailView, ScheduleEditView, LoginView, ScheduleListView, LogoutView, \
    ScheduleCheckoutView, ScheduleAdd, PersonAdd, GroupAdd, UserAdd, PersonListView, GroupListView, ShiftAddView, \
    ShiftDeleteView, ScheduleDeleteView, UserDeleteView, PersonEditView, PrintPDFView

urlpatterns = [
    path('detail/<int:schedule_id>/', ScheduleDetailView.as_view(), name='schedule-detail'),
    path('edit/<int:schedule_id>/', ScheduleEditView.as_view(), name='schedule-edit'),
    path('checkout/<int:schedule_id>/', ScheduleCheckoutView.as_view(), name='schedule-checkout'),
    path('login/', LoginView.as_view(), name='login'),
    path('all/', ScheduleListView.as_view(), name='schedule-list'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('add/', ScheduleAdd.as_view(), name='schedule-add'),
    path('person/add/', PersonAdd.as_view(), name='person-add'),
    path('person/all', PersonListView.as_view(), name='person-all'),
    path('group/add/', GroupAdd.as_view(), name='group-add'),
    path('user/add/', UserAdd.as_view(), name='user-add'),
    path('group/all/', GroupListView.as_view(), name='group-all'),
    path('shift/add/', ShiftAddView.as_view(), name='shift-add'),
    path('shift/delete/<int:shift_id>/', ShiftDeleteView.as_view(), name='shift-delete'),
    path('delete/<int:schedule_id>/', ScheduleDeleteView.as_view(), name='schedule-delete'),
    path('user/delete/<int:user_id>/', UserDeleteView.as_view(), name='user-delete'),
    path('person/edit/<int:person_id>/', PersonEditView.as_view(), name='person-edit'),
    path('print/<int:schedule_id>/', PrintPDFView.as_view(), name='print')
]
