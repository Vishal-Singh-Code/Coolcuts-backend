from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Service(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    
    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="appointments")

    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    booking_time = models.DateTimeField(default=timezone.now) 
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["appointment_date", "appointment_time"],
                name="unique_appointment_slot",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.service.name} ({self.appointment_date} {self.appointment_time})"
    
    
class ChecklistItem(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        related_name="checklist",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    done = models.BooleanField(default=False)

    
class ContactForm(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} regarding {self.subject}"
