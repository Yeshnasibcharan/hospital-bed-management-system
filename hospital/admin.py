from django.contrib import admin
from .models import Ward, Bed, Patient, Admission, CleaningRequest, Notification

admin.site.register(Ward)
admin.site.register(Bed)
admin.site.register(Patient)
admin.site.register(Admission)
admin.site.register(CleaningRequest)
admin.site.register(Notification)