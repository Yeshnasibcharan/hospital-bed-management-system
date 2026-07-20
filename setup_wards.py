from django.contrib.auth.models import User
from hospital.models import Ward, Bed

ward_data = [
    ("Male Medical Ward 1", "MM1", "male"),
    ("Male Medical Ward 2", "MM2", "male"),
    ("Female Medical Ward 1", "FM1", "female"),
    ("Female Medical Ward 2", "FM2", "female"),
    ("Male Surgical Ward", "MS", "male"),
    ("Female Surgical Ward", "FS", "female"),
    ("Male Orthopedic Ward", "MO", "male"),
    ("Female Orthopedic Ward", "FO", "female"),
    ("Male Cardiac Ward", "MC", "male"),
    ("Female Cardiac Ward", "FC", "female"),
    ("Gyne Ward", "GY", "female"),
    ("Maternity Ward", "MT", "female"),
    ("Pediatric Ward", "PD", "mixed"),
    ("Nursery Ward", "NS", "mixed"),
    ("ICU", "ICU", "mixed"),
]

for name, code, gender in ward_data:
    ward, _ = Ward.objects.get_or_create(code=code, defaults={"name": name, "gender_restriction": gender})

    for i in range(1, 13):
        bed_number = f"{code}{i:03d}"
        Bed.objects.get_or_create(ward=ward, bed_number=bed_number)

    nurse_username = f"{name.replace(' ', '_')}_Nurse"
    if not User.objects.filter(username=nurse_username).exists():
        nurse = User.objects.create_user(username=nurse_username, password="nurse")
        nurse.profile.role = "nurse"
        nurse.profile.assigned_ward = ward
        nurse.profile.save()

    cleaner_username = f"{name.replace(' ', '_')}_Cleaner"
    if not User.objects.filter(username=cleaner_username).exists():
        cleaner = User.objects.create_user(username=cleaner_username, password="cleaner")
        cleaner.profile.role = "cleaner"
        cleaner.profile.assigned_ward = ward
        cleaner.profile.save()

    print(f"{name}: ward + 12 beds + nurse/cleaner accounts ready")

print("All wards set up.")