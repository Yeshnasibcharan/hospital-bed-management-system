import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import random
from datetime import timedelta
from django.utils import timezone
from hospital.models import Ward, Bed, Patient, Admission

first_names_m = ['Rajesh', 'Vikram', 'Arjun', 'Sanjay', 'Deepak', 'Ravi', 'Kiran', 'Ashok', 'Suresh', 'Manoj']
first_names_f = ['Priya', 'Anjali', 'Kavita', 'Sunita', 'Meera', 'Pooja', 'Neha', 'Divya', 'Rekha', 'Shalini']
last_names = ['Ramgoolam', 'Bunwaree', 'Callychurn', 'Jugnauth', 'Seebaluck', 'Bissessur', 'Gungah', 'Naidoo', 'Appadoo', 'Ramsamy']

now = timezone.now()
created_count = 0

for ward in Ward.objects.all():
    beds = list(ward.beds.all())
    for _ in range(random.randint(3, 6)):
        bed = random.choice(beds)

        if ward.gender_restriction == 'male':
            gender = 'M'
        elif ward.gender_restriction == 'female':
            gender = 'F'
        else:
            gender = random.choice(['M', 'F'])

        first = random.choice(first_names_m if gender == 'M' else first_names_f)
        last = random.choice(last_names)
        full_name = f"{first} {last}"

        days_ago = random.randint(0, 18)
        hour_weight = random.choices(
            population=list(range(24)),
            weights=[1,1,1,1,1,2,3,5,7,8,6,5,4,4,5,6,7,8,6,4,3,2,1,1],
            k=1
        )[0]
        admission_dt = now - timedelta(days=days_ago)
        admission_dt = admission_dt.replace(hour=hour_weight, minute=random.randint(0, 59))

        patient = Patient.objects.create(
            full_name=full_name,
            gender=gender,
            date_of_birth=timezone.datetime(random.randint(1940, 2005), random.randint(1, 12), random.randint(1, 28)).date(),
            contact_number='DEMO-SEED',
        )

        will_discharge = random.random() < 0.7
        discharge_dt = None
        is_active = True
        if will_discharge and days_ago > 0:
            stay_hours = random.uniform(4, min(days_ago * 24, 240))
            candidate_discharge = admission_dt + timedelta(hours=stay_hours)
            if candidate_discharge < now:
                discharge_dt = candidate_discharge
                is_active = False

        Admission.objects.create(
            patient=patient,
            bed=bed,
            admission_date=admission_dt,
            discharge_date=discharge_dt,
            is_active=is_active,
        )
        created_count += 1

print(f"Created {created_count} seeded admissions.")
