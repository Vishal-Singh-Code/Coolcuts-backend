from datetime import date, time

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Appointment, ChecklistItem, Service


class AppointmentApiHardeningTests(APITestCase):
    def setUp(self):
        self.user_one = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="Strong@123",
        )
        self.user_two = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="Strong@123",
        )
        self.staff_user = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="Strong@123",
            is_staff=True,
        )

        self.service = Service.objects.create(name="Haircut", price=500)

        self.book_url = reverse("appointment-book")
        self.detail_url = lambda pk: reverse("appointment-detail", kwargs={"pk": pk})
        self.list_url = reverse("appointment-list")

    def test_same_slot_cannot_be_booked_by_two_different_users(self):
        payload = {
            "service": self.service.id,
            "appointment_date": "2026-03-01",
            "appointment_time": "10:00:00",
        }

        self.client.force_authenticate(user=self.user_one)
        first_response = self.client.post(self.book_url, payload, format="json")
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.user_two)
        second_response = self.client.post(self.book_url, payload, format="json")
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            Appointment.objects.filter(
                appointment_date=date(2026, 3, 1),
                appointment_time=time(10, 0),
            ).count(),
            1,
        )

    def test_non_staff_cannot_change_appointment_status(self):
        appointment = Appointment.objects.create(
            user=self.user_one,
            service=self.service,
            appointment_date=date(2026, 3, 2),
            appointment_time=time(11, 0),
            status="pending",
        )

        self.client.force_authenticate(user=self.user_one)
        response = self.client.patch(
            self.detail_url(appointment.id),
            {"status": "done"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "pending")

    def test_staff_can_change_appointment_status(self):
        appointment = Appointment.objects.create(
            user=self.user_one,
            service=self.service,
            appointment_date=date(2026, 3, 3),
            appointment_time=time(12, 0),
            status="pending",
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.patch(
            self.detail_url(appointment.id),
            {"status": "done"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "done")

    def test_list_endpoint_does_not_create_checklist_items(self):
        appointment = Appointment.objects.create(
            user=self.user_one,
            service=self.service,
            appointment_date=date(2026, 3, 4),
            appointment_time=time(13, 0),
            status="pending",
        )
        self.assertEqual(ChecklistItem.objects.filter(appointment=appointment).count(), 0)

        self.client.force_authenticate(user=self.user_one)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ChecklistItem.objects.filter(appointment=appointment).count(), 0)

    def test_available_slots_excludes_done_appointments_too(self):
        Appointment.objects.create(
            user=self.user_one,
            service=self.service,
            appointment_date=date(2026, 3, 6),
            appointment_time=time(9, 0),
            status="done",
        )

        self.client.force_authenticate(user=self.user_one)
        response = self.client.get(
            reverse("available-slots"),
            {"date": "2026-03-06"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("09:00", response.data)

    def test_customer_name_uses_profile_name(self):
        self.user_one.profile.name = "Vishal Singh"
        self.user_one.profile.save(update_fields=["name"])

        Appointment.objects.create(
            user=self.user_one,
            service=self.service,
            appointment_date=date(2026, 3, 5),
            appointment_time=time(14, 0),
            status="pending",
        )

        self.client.force_authenticate(user=self.user_one)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["customer_name"], "Vishal Singh")
