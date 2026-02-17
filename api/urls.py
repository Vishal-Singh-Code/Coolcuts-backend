from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentListView,
    AppointmentDetailView,
    BookAppointmentView,
    ServiceViewSet,
    contact_form,
    ChecklistItemToggleView,
    AvailableSlotsView,

)

router = DefaultRouter()
router.register(r"services", ServiceViewSet, basename="service")

urlpatterns = [
    # Services
    path("", include(router.urls)),

    # Appointments
    path("appointments/", AppointmentListView.as_view(), name="appointment-list"),
    path("appointments/book/", BookAppointmentView.as_view(), name="appointment-book"),
    path("appointments/<int:pk>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path("checklist-items/<int:pk>/toggle/", ChecklistItemToggleView.as_view()),

    # Contact
    path("contact/", contact_form, name="contact-form"),

    path("appointments/available-slots/",AvailableSlotsView.as_view(),name="available-slots"),
]
