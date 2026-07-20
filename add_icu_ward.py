import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from hospital.models import Ward, Bed
from django.contrib.auth.models import User
from accounts.models import Profile

ward, created = Ward.objects.get_or_create(
    code='ICU',
    defaults={'name': 'ICU', 'gender_restriction': 'mixed'}
)
print(f"Ward '{ward.name}' created: {created}")

for i in range(1, 13):
    bed_number = f"ICU{i:03d}"
    bed, bed_created = Bed.objects.get_or_create(
        ward=ward,
        bed_number=bed_number,
    )
print(f"ICU now has {ward.beds.count()} beds")

nurse_username = "ICU_Nurse"
if not User.objects.filter(username=nurse_username).exists():
    nurse_user = User.objects.create_user(username=nurse_username, password="nurse")
    nurse_user.profile.role = 'nurse'
    nurse_user.profile.assigned_ward = ward
    nurse_user.profile.save()
    print(f"Created nurse account: {nurse_username}")
else:
    print(f"Nurse account {nurse_username} already exists")

cleaner_username = "ICU_Cleaner"
if not User.objects.filter(username=cleaner_username).exists():
    cleaner_user = User.objects.create_user(username=cleaner_username, password="cleaner")
    cleaner_user.profile.role = 'cleaner'
    cleaner_user.profile.assigned_ward = ward
    cleaner_user.profile.save()
    print(f"Created cleaner account: {cleaner_username}")
else:
    print(f"Cleaner account {cleaner_username} already exists")

print("Done.")
