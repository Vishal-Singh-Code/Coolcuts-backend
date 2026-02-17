from rest_framework import serializers
from django.db import IntegrityError, transaction

from .models import Appointment , Service, ContactForm, ChecklistItem

class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ["id", "name", "done"]


class AppointmentSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    price = serializers.IntegerField(source="service.price", read_only=True)
    services = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )
    selected_services = serializers.SerializerMethodField()

    customer_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    checklist = ChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "service",
            "service_name",
            "price",
            "services",
            "selected_services",
            "customer_name",
            "phone",
            "appointment_date",
            "appointment_time",
            "status",
            "checklist",
        ]
        extra_kwargs = {
            "service": {"required": False},
        }

    # ✅ name comes from profile / user
    def get_customer_name(self, obj):
        user = obj.user
        profile = getattr(user, "profile", None)
        if profile and str(profile.name).strip():
            return profile.name.strip()
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name or user.username

    # ✅ phone comes from profile
    def get_phone(self, obj):
        profile = getattr(obj.user, "profile", None)
        return profile.phone if profile else ""

    def get_selected_services(self, obj):
        checklist_names = [item.name for item in obj.checklist.all()]
        if checklist_names:
            return checklist_names
        return [obj.service.name]

    def validate(self, data):
        request = self.context["request"]
        selected_services = data.get("services", [])
        selected_service_ids = list(dict.fromkeys(selected_services))

        if not self.instance and not selected_service_ids and not data.get("service"):
            raise serializers.ValidationError({"services": "Select at least one service."})

        if selected_service_ids:
            matched_count = Service.objects.filter(id__in=selected_service_ids).count()
            if matched_count != len(selected_service_ids):
                raise serializers.ValidationError({"services": "One or more selected services are invalid."})

        # Keep validation safe for both create and partial update.
        date = data.get(
            "appointment_date",
            self.instance.appointment_date if self.instance else None
        )
        time = data.get(
            "appointment_time",
            self.instance.appointment_time if self.instance else None
        )

        if date and time:
            conflict_qs = Appointment.objects.filter(
                appointment_date=date,
                appointment_time=time,
            )
            if self.instance:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)
            if conflict_qs.exists():
                raise serializers.ValidationError("This time slot is already booked.")

        if "status" in data and not request.user.is_staff:
            raise serializers.ValidationError({"status": "Only staff can change appointment status."})

        return data 
    
    def create(self, validated_data):
        user = self.context["request"].user
        service_ids = list(dict.fromkeys(validated_data.pop("services", [])))

        selected_service_objects = []
        if service_ids:
            service_map = Service.objects.in_bulk(service_ids)
            selected_service_objects = [service_map[service_id] for service_id in service_ids if service_id in service_map]

        primary_service = selected_service_objects[0] if selected_service_objects else validated_data.get("service")
        validated_data["service"] = primary_service
        checklist_items = [service.name for service in selected_service_objects] if selected_service_objects else [primary_service.name]

        try:
            with transaction.atomic():
                appointment = Appointment.objects.create(user=user, **validated_data)
                ChecklistItem.objects.bulk_create(
                    [
                        ChecklistItem(appointment=appointment, name=item_name)
                        for item_name in checklist_items
                    ]
                )
                return appointment
        except IntegrityError:
            raise serializers.ValidationError("This time slot is already booked.")

    def update(self, instance, validated_data):
        validated_data.pop("services", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            with transaction.atomic():
                instance.save()
                return instance
        except IntegrityError:
            raise serializers.ValidationError("This time slot is already booked.")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price']


class ContactFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactForm
        fields = ['name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ["created_at"]
