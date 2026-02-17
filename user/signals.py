from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, name=instance.username)


@receiver(pre_save, sender=User)
def normalize_and_enforce_unique_email(sender, instance, **kwargs):
    email = (instance.email or "").strip().lower()
    instance.email = email
    if not email:
        return

    duplicate_exists = User.objects.filter(email__iexact=email).exclude(pk=instance.pk).exists()
    if duplicate_exists:
        raise ValidationError({"email": "A user with this email already exists."})
