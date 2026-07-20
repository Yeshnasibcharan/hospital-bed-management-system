from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('nurse', 'Nurse'),
        ('cleaner', 'Cleaner'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='nurse')
    assigned_ward = models.ForeignKey(
        'hospital.Ward', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_nurses',
        help_text="For Nurse accounts only: restricts this nurse's dashboard to a single ward."
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()