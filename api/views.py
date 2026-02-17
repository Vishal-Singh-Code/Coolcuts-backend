from datetime import time

from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from .models import Appointment, Service, ChecklistItem
from .serializers import AppointmentSerializer, ServiceSerializer, ContactFormSerializer


def get_appointment_queryset_for_user(user):
    queryset = Appointment.objects.select_related(
        "service",
        "user",
        "user__profile",
    ).prefetch_related("checklist")
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(user=user)


# ---------------------------------------------------
# Appointment Create
# ---------------------------------------------------
class BookAppointmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppointmentSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Appointment booked successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        if not date:
            return Response({"detail": "Date required"}, status=400)

        all_slots = [
            time(hour, minute)
            for hour in range(9, 19)
            for minute in (0, 30)
        ]

        booked_slots = Appointment.objects.filter(
            appointment_date=date,
        ).values_list("appointment_time", flat=True)

        available = [
            slot.strftime("%H:%M")
            for slot in all_slots
            if slot not in booked_slots
        ]

        return Response(available)


# ---------------------------------------------------
# Appointment List
# ---------------------------------------------------
class AppointmentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return get_appointment_queryset_for_user(self.request.user)


# ---------------------------------------------------
# Appointment Detail (Retrieve, Update, Delete)
# ---------------------------------------------------
class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return get_appointment_queryset_for_user(self.request.user)


# ---------------------------------------------------
# Service ViewSet (Admin Only for Write)
# ---------------------------------------------------
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return []  # GET allowed for all users


# ---------------------------------------------------
# Contact Form (Public)
# ---------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def contact_form(request):
    serializer = ContactFormSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Contact form submitted successfully!"},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChecklistItemToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            item = ChecklistItem.objects.get(pk=pk)
        except ChecklistItem.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        # Optional: admin-only
        if not request.user.is_staff:
            return Response({"detail": "Forbidden"}, status=403)

        item.done = not item.done
        item.save()

        return Response({
            "id": item.id,
            "done": item.done
        })
