from django.contrib import admin
from .models import Appointment ,Service ,ContactForm

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'appointment_date', 'appointment_time')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display =('name' , 'price')

@admin.register(ContactForm)
class ContactFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'message','created_at')

