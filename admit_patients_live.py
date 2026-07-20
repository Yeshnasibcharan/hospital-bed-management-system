import random
from hospital.models import Ward, Bed, Patient, Admission

first_names_m = ["Rajesh", "Vikram", "Arjun", "Sanjay", "Deepak", "Ravi", "Kiran", "Ashok", "Suresh", "Manoj"]
first_names_f = ["Priya", "Anjali", "Kavita", "Sunita", "Meera", "Pooja", "Neha", "Divya", "Rekha", "Shalini"]
last_names = ["Ramgoolam", "Bunwaree", "Callychurn", "Jugnauth", "Seebaluck", "Bissessur", "Gungah", "Naidoo", "Appadoo", "Ramsamy"]

medications_morning = ["Paracetamol 500mg", "Amoxicillin 250mg", "Metformin 500mg", "Aspirin 75mg", "Omeprazole 20mg"]
medications_afternoon = ["Insulin 10u", "Ibuprofen 400mg", "Losartan 50mg", "Cetirizine 10mg"]
medications_evening = ["Amlodipine 5mg", "Atorvastatin 20mg", "Salbutamol inhaler", "Diazepam 5mg"]

admin_user = None

created_count = 0

for ward in Ward.objects.all():
    available_beds = list(ward.beds.filter(status="available").order_by("bed_number")[:6])

    for bed in available_beds:
        if ward.gender_restriction == "male":
            gender = "M"
        elif ward.gender_restriction == "female":
            gender = "F"
        else:
            gender = random.choice(["M", "F"])

        first = random.choice(first_names_m if gender == "M" else first_names_f)
        last = random.choice(last_names)
        full_name = f"{first} {last}"

        patient = Patient.objects.create(
            full_name=full_name,
            gender=gender,
            date_of_birth=f"{random.randint(1945, 2010)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            contact_number="5" + str(random.randint(1000000, 9999999)),
        )

        Admission.objects.create(
            patient=patient,
            bed=bed,
            admitted_by=admin_user,
            medication_morning=random.choice(medications_morning),
            medication_afternoon=random.choice(medications_afternoon),
            medication_evening=random.choice(medications_evening),
        )

        bed.status = "occupied"
        bed.save()
        created_count += 1

    print(f"{ward.name}: admitted {len(available_beds)} patients")

print(f"Total patients admitted: {created_count}")