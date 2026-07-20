from django.conf import settings
from django.db import models


class Ward(models.Model):
    GENDER_RESTRICTION_CHOICES = [
        ('male', 'Male Only'),
        ('female', 'Female Only'),
        ('mixed', 'Mixed'),
    ]

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=5,
        unique=True,
        help_text="Short code used as a prefix in bed numbers, e.g. 'MM' for Male Medical"
    )
    gender_restriction = models.CharField(
        max_length=10,
        choices=GENDER_RESTRICTION_CHOICES,
        default='mixed',
        help_text="Male-only or Female-only wards auto-assign patient gender on admission. Mixed wards (e.g. Pediatric) require manual selection."
    )

    def __str__(self):
        return self.name


class Bed(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning Required'),
        ('reserved', 'Reserved'),
        ('out_of_service', 'Out of Service'),
    ]

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=10, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    has_guardian_space = models.BooleanField(
        default=False,
        help_text="Bed includes a sleeper chair/pull-out bed for a parent or guardian to stay overnight (Pediatric Ward)."
    )

    def __str__(self):
        return self.bed_number


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class Admission(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='admissions')
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='admissions_created'
    )
    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    medication_morning = models.CharField(max_length=255, blank=True)
    medication_afternoon = models.CharField(max_length=255, blank=True)
    medication_evening = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.patient.full_name} - {self.bed.bed_number}"


class CleaningRequest(models.Model):
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='cleaning_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    cleaned_at = models.DateTimeField(null=True, blank=True)
    cleaned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cleaning_completed'
    )
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Cleaning: {self.bed.bed_number} ({'Done' if self.is_completed else 'Pending'})"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('discharge', 'Patient Discharged'),
        ('cleaning_required', 'Bed Requires Cleaning'),
        ('bed_available', 'Bed Available'),
        ('ward_full', 'Ward Full'),
        ('ward_almost_full', 'Ward Almost Full'),
        ('bed_shortage_forecast', 'Predicted Bed Shortage'),
    ]

    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.CharField(max_length=255)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message


class MedicationCheck(models.Model):
    TIME_SLOT_CHOICES = [
        ('morning', 'Morning'),
        ('noon', 'Noon'),
        ('evening', 'Evening'),
    ]

    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='medication_checks')
    date = models.DateField()
    time_slot = models.CharField(max_length=10, choices=TIME_SLOT_CHOICES)
    is_given = models.BooleanField(default=False)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='medication_checks'
    )
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('bed', 'date', 'time_slot')

    def __str__(self):
        return f"{self.bed.bed_number} - {self.date} {self.get_time_slot_display()}"