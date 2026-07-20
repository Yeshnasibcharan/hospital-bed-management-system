from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json
import csv
from django.http import HttpResponse
from .models import Ward, Bed, Patient, Admission, Notification, MedicationCheck
from .forms import AdmitPatientForm, TransferPatientForm
from .models import Ward, Bed, Patient, Admission, Notification, MedicationCheck, MealCheck

def check_ward_capacity(ward):
    total = ward.beds.count()
    occupied = ward.beds.filter(status='occupied').count()

    if total == 0:
        return

    occupancy_ratio = occupied / total

    if occupancy_ratio == 1.0:
        Notification.objects.create(
            notification_type='ward_full',
            message=f"{ward.name} is now full ({occupied}/{total} beds occupied).",
            ward=ward,
        )
    elif occupancy_ratio >= 0.8:
        Notification.objects.create(
            notification_type='ward_almost_full',
            message=f"{ward.name} is almost full ({occupied}/{total} beds occupied).",
            ward=ward,
        )


def build_admission_trend(days_back=14, days_forward=3):
    today = timezone.now().date()
    start_date = today - timedelta(days=days_back - 1)

    labels = []
    actual_counts = []

    for i in range(days_back):
        day = start_date + timedelta(days=i)
        count = Admission.objects.filter(admission_date__date=day).count()
        labels.append(day.strftime('%b %d'))
        actual_counts.append(count)

    recent_window = actual_counts[-7:] if len(actual_counts) >= 7 else actual_counts
    avg = sum(recent_window) / len(recent_window) if recent_window else 0

    forecast_labels = []
    forecast_counts = []
    for i in range(1, days_forward + 1):
        day = today + timedelta(days=i)
        forecast_labels.append(day.strftime('%b %d'))
        forecast_counts.append(round(avg, 1))

    return {
        'labels': labels + forecast_labels,
        'actual': actual_counts + [None] * days_forward,
        'forecast': [None] * (days_back - 1) + [actual_counts[-1]] + forecast_counts,
    }


def check_forecast_alarm(ward):
    total_beds = ward.beds.count()
    if total_beds == 0:
        return

    occupied_now = ward.beds.filter(status='occupied').count()
    recent_admissions = Admission.objects.filter(
        bed__ward=ward,
        admission_date__gte=timezone.now() - timedelta(days=7)
    ).count()
    avg_daily = recent_admissions / 7

    projected_in_3_days = occupied_now + (avg_daily * 3)
    projected_ratio = projected_in_3_days / total_beds

    if projected_ratio >= 0.9:
        already_alerted_recently = Notification.objects.filter(
            ward=ward,
            notification_type='bed_shortage_forecast',
            created_at__gte=timezone.now() - timedelta(hours=6)
        ).exists()

        if not already_alerted_recently:
            Notification.objects.create(
                notification_type='bed_shortage_forecast',
                message=f"Forecast alert: {ward.name} is projected to near full capacity within 3 days based on recent admission trends.",
                ward=ward,
            )


def _time_ago_string(dt):
    if not dt:
        return ''
    diff = timezone.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    days = int(hours // 24)
    return f"{days}d ago"


def _build_admin_dashboard_data():
    from django.db.models.functions import ExtractHour
    from django.db.models import Count, Q

    total_beds = Bed.objects.count()
    available_beds = Bed.objects.filter(status='available').count()
    occupied_beds = Bed.objects.filter(status='occupied').count()
    cleaning_beds = Bed.objects.filter(status='cleaning').count()
    reserved_beds = Bed.objects.filter(status='reserved').count()
    out_of_service_beds = Bed.objects.filter(status='out_of_service').count()

    total_patients_admitted = Admission.objects.count()
    currently_admitted = Admission.objects.filter(is_active=True).count()
    total_discharged = Admission.objects.filter(is_active=False).count()

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    admissions_today = Admission.objects.filter(admission_date__date=today).count()
    admissions_yesterday = Admission.objects.filter(admission_date__date=yesterday).count()
    admissions_trend = admissions_today - admissions_yesterday

    discharges_today = Admission.objects.filter(discharge_date__date=today).count()
    discharges_yesterday = Admission.objects.filter(discharge_date__date=yesterday).count()
    discharges_trend = discharges_today - discharges_yesterday

    admissions_last_24h = Admission.objects.filter(
        admission_date__gte=timezone.now() - timedelta(hours=24)
    ).count()
    discharges_last_24h = Admission.objects.filter(
        discharge_date__gte=timezone.now() - timedelta(hours=24)
    ).count()
    occupied_beds_24h_ago = occupied_beds - admissions_last_24h + discharges_last_24h
    occupied_trend = occupied_beds - occupied_beds_24h_ago

    occupancy_pct_now = round((occupied_beds / total_beds * 100), 1) if total_beds else 0

    status_pie_data = [
        {'value': available_beds, 'name': 'Available'},
        {'value': occupied_beds, 'name': 'Occupied'},
        {'value': cleaning_beds, 'name': 'Cleaning Required'},
        {'value': reserved_beds, 'name': 'Reserved'},
        {'value': out_of_service_beds, 'name': 'Out of Service'},
    ]

    male_patients = Admission.objects.filter(is_active=True, patient__gender='M').count()
    female_patients = Admission.objects.filter(is_active=True, patient__gender='F').count()
    patient_gender_pie_data = [
        {'value': male_patients, 'name': 'Male Patients'},
        {'value': female_patients, 'name': 'Female Patients'},
    ]

    wards = Ward.objects.all()
    ward_names = []
    ward_occupied = []
    ward_available = []
    ward_breakdown = []

    for ward in wards:
        total = ward.beds.count()
        occ = ward.beds.filter(status='occupied').count()
        avail = ward.beds.filter(status='available').count()
        clean = ward.beds.filter(status='cleaning').count()
        oos = ward.beds.filter(status='out_of_service').count()
        pct = round((occ / total * 100), 1) if total else 0

        ward_names.append(ward.name)
        ward_occupied.append(occ)
        ward_available.append(avail)

        ward_breakdown.append({
            'name': ward.name, 'total': total, 'occupied': occ,
            'available': avail, 'cleaning': clean, 'out_of_service': oos, 'pct': pct,
        })

    trend = build_admission_trend()

    recent_activity_qs = Notification.objects.order_by('-created_at')[:8]
    recent_activity = []
    for a in recent_activity_qs:
        recent_activity.append({
            'message': a.message,
            'time_ago': _time_ago_string(a.created_at),
        })

    recent_admissions_qs = Admission.objects.select_related(
        'patient', 'bed', 'bed__ward', 'admitted_by'
    ).order_by('-admission_date')[:8]
    recent_admissions = []
    for a in recent_admissions_qs:
        recent_admissions.append({
            'patient_name': a.patient.full_name,
            'bed_id': a.bed.id,
            'ward_bed': f"{a.bed.ward.name} - {a.bed.bed_number}",
            'gender': a.patient.get_gender_display(),
            'admitted_by': a.admitted_by.username if a.admitted_by else '—',
            'admission_date': timezone.localtime(a.admission_date).strftime('%b %d, %H:%M'),
            'is_active': a.is_active,
        })

    hourly_counts = Admission.objects.annotate(
        hour=ExtractHour('admission_date')
    ).values('hour').annotate(count=Count('id')).order_by('hour')
    hour_labels = [f"{h:02d}:00" for h in range(24)]
    hour_data = [0] * 24
    for entry in hourly_counts:
        hour_data[entry['hour']] = entry['count']

    los_labels = []
    los_data = []
    for ward in wards:
        discharged = Admission.objects.filter(bed__ward=ward, is_active=False, discharge_date__isnull=False)
        total_hours = 0
        count = 0
        for adm in discharged:
            duration = adm.discharge_date - adm.admission_date
            total_hours += duration.total_seconds() / 3600
            count += 1
        avg_hours = round(total_hours / count, 1) if count else 0
        los_labels.append(ward.name)
        los_data.append(avg_hours)

    notif_type_counts = Notification.objects.values('notification_type').annotate(count=Count('id'))
    notif_type_display = dict(Notification.NOTIFICATION_TYPES)
    notif_labels = [notif_type_display.get(n['notification_type'], n['notification_type']) for n in notif_type_counts]
    notif_data = [n['count'] for n in notif_type_counts]

    trend_days = 14
    day_list = [today - timedelta(days=i) for i in range(trend_days - 1, -1, -1)]
    gender_trend_labels = [d.strftime('%b %d') for d in day_list]

    gender_trend_male = []
    gender_trend_female = []
    for d in day_list:
        m = Admission.objects.filter(admission_date__date=d, patient__gender='M').count()
        f = Admission.objects.filter(admission_date__date=d, patient__gender='F').count()
        gender_trend_male.append(m)
        gender_trend_female.append(f)

    key_wards = list(Ward.objects.all().order_by('name')[:4])
    ward_occupancy_trend_series = []
    for ward in key_wards:
        ward_total = ward.beds.count()
        series_pct = []
        for d in day_list:
            occ_count = Admission.objects.filter(
                bed__ward=ward, admission_date__date__lte=d
            ).filter(
                Q(discharge_date__isnull=True) | Q(discharge_date__date__gt=d)
            ).count()
            pct = round((occ_count / ward_total * 100), 1) if ward_total else 0
            series_pct.append(pct)
        ward_occupancy_trend_series.append({'name': ward.name, 'data': series_pct})

    latest_notification = Notification.objects.order_by('-id').first()

    return {
        'total_beds': total_beds,
        'available_beds': available_beds,
        'occupied_beds': occupied_beds,
        'cleaning_beds': cleaning_beds,
        'total_patients_admitted': total_patients_admitted,
        'currently_admitted': currently_admitted,
        'total_discharged': total_discharged,
        'admissions_today': admissions_today,
        'admissions_trend': admissions_trend,
        'discharges_today': discharges_today,
        'discharges_trend': discharges_trend,
        'occupied_trend': occupied_trend,
        'occupancy_pct_now': occupancy_pct_now,
        'ward_breakdown': ward_breakdown,
        'recent_activity': recent_activity,
        'recent_admissions': recent_admissions,
        'status_pie_data': status_pie_data,
        'ward_names': ward_names,
        'ward_occupied': ward_occupied,
        'ward_available': ward_available,
        'trend_labels': trend['labels'],
        'trend_actual': trend['actual'],
        'trend_forecast': trend['forecast'],
        'patient_gender_pie_data': patient_gender_pie_data,
        'hour_labels': hour_labels,
        'hour_data': hour_data,
        'los_labels': los_labels,
        'los_data': los_data,
        'notif_labels': notif_labels,
        'notif_data': notif_data,
        'gender_trend_labels': gender_trend_labels,
        'gender_trend_male': gender_trend_male,
        'gender_trend_female': gender_trend_female,
        'ward_occupancy_trend_series': ward_occupancy_trend_series,
        'latest_notification_id': latest_notification.id if latest_notification else 0,
    }


@login_required
def admin_dashboard(request):
    data = _build_admin_dashboard_data()
    context = {
        'total_beds': data['total_beds'],
        'available_beds': data['available_beds'],
        'occupied_beds': data['occupied_beds'],
        'cleaning_beds': data['cleaning_beds'],
        'total_patients_admitted': data['total_patients_admitted'],
        'currently_admitted': data['currently_admitted'],
        'total_discharged': data['total_discharged'],
        'admissions_today': data['admissions_today'],
        'admissions_trend': data['admissions_trend'],
        'discharges_today': data['discharges_today'],
        'discharges_trend': data['discharges_trend'],
        'occupied_trend': data['occupied_trend'],
        'occupancy_pct_now': data['occupancy_pct_now'],
        'ward_breakdown': data['ward_breakdown'],
        'recent_activity': data['recent_activity'],
        'recent_admissions': data['recent_admissions'],
        'all_wards': Ward.objects.all(),
        'status_pie_data': json.dumps(data['status_pie_data']),
        'ward_names': json.dumps(data['ward_names']),
        'ward_occupied': json.dumps(data['ward_occupied']),
        'ward_available': json.dumps(data['ward_available']),
        'trend_labels': json.dumps(data['trend_labels']),
        'trend_actual': json.dumps(data['trend_actual']),
        'trend_forecast': json.dumps(data['trend_forecast']),
        'patient_gender_pie_data': json.dumps(data['patient_gender_pie_data']),
        'hour_labels': json.dumps(data['hour_labels']),
        'hour_data': json.dumps(data['hour_data']),
        'los_labels': json.dumps(data['los_labels']),
        'los_data': json.dumps(data['los_data']),
        'notif_labels': json.dumps(data['notif_labels']),
        'notif_data': json.dumps(data['notif_data']),
        'gender_trend_labels': json.dumps(data['gender_trend_labels']),
        'gender_trend_male': json.dumps(data['gender_trend_male']),
        'gender_trend_female': json.dumps(data['gender_trend_female']),
        'ward_occupancy_trend_series': json.dumps(data['ward_occupancy_trend_series']),
    }
    return render(request, 'hospital/admin_dashboard.html', context)


@login_required
def admin_dashboard_data(request):
    return JsonResponse(_build_admin_dashboard_data())


@login_required
def export_bed_status_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="bed_status_{timezone.now().date()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ward', 'Bed Number', 'Status', 'Patient', 'Gender', 'Admitted On'])

    beds = Bed.objects.select_related('ward').order_by('ward__name', 'bed_number')
    for bed in beds:
        admission = bed.admissions.filter(is_active=True).first()
        writer.writerow([
            bed.ward.name,
            bed.bed_number,
            bed.get_status_display(),
            admission.patient.full_name if admission else '',
            admission.patient.get_gender_display() if admission else '',
            timezone.localtime(admission.admission_date).strftime('%Y-%m-%d %H:%M') if admission else '',
        ])

    return response


@login_required
def export_admission_history_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="admission_history_{timezone.now().date()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Patient', 'Gender', 'Ward', 'Bed', 'Admitted By', 'Admission Date', 'Discharge Date', 'Status'])

    admissions = Admission.objects.select_related(
        'patient', 'bed', 'bed__ward', 'admitted_by'
    ).order_by('-admission_date')

    for a in admissions:
        writer.writerow([
            a.patient.full_name,
            a.patient.get_gender_display(),
            a.bed.ward.name,
            a.bed.bed_number,
            a.admitted_by.username if a.admitted_by else '',
            timezone.localtime(a.admission_date).strftime('%Y-%m-%d %H:%M'),
            timezone.localtime(a.discharge_date).strftime('%Y-%m-%d %H:%M') if a.discharge_date else '',
            'Active' if a.is_active else 'Discharged',
        ])

    return response


@login_required
def nurse_dashboard(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    query = request.GET.get('q', '').strip()
    search_results = None

    if assigned_ward:
        if query:
            search_results = Admission.objects.filter(
                is_active=True,
                bed__ward=assigned_ward,
                patient__full_name__icontains=query
            ).select_related('patient', 'bed', 'bed__ward')

        beds = assigned_ward.beds.select_related().order_by('bed_number')
        for bed in beds:
            bed.active_admission = bed.admissions.filter(is_active=True).first()

        recent_notifications = Notification.objects.filter(ward=assigned_ward).order_by('-created_at')[:5]

        return render(request, 'hospital/nurse_dashboard.html', {
            'assigned_ward': assigned_ward,
            'beds': beds,
            'query': query,
            'search_results': search_results,
            'notifications': recent_notifications,
        })

    wards = Ward.objects.all()
    if query:
        search_results = Admission.objects.filter(
            is_active=True,
            patient__full_name__icontains=query
        ).select_related('patient', 'bed', 'bed__ward')

    recent_notifications = Notification.objects.order_by('-created_at')[:5]

    return render(request, 'hospital/nurse_dashboard.html', {
        'assigned_ward': None,
        'wards': wards,
        'query': query,
        'search_results': search_results,
        'notifications': recent_notifications,
    })


@login_required
def medication_sheet(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if not assigned_ward:
        messages.error(request, "No ward assigned to your account.")
        return redirect('nurse_dashboard')

    today = timezone.now().date()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    beds = assigned_ward.beds.order_by('bed_number')

    if request.method == 'POST':
        for bed in beds:
            for date in week_dates:
                for slot, _ in MedicationCheck.TIME_SLOT_CHOICES:
                    checkbox_name = f"check_{bed.id}_{date.isoformat()}_{slot}"
                    is_checked = checkbox_name in request.POST

                    record, created = MedicationCheck.objects.get_or_create(
                        bed=bed, date=date, time_slot=slot,
                        defaults={'is_given': is_checked}
                    )
                    if record.is_given != is_checked:
                        record.is_given = is_checked
                        record.checked_by = request.user if is_checked else None
                        record.checked_at = timezone.now() if is_checked else None
                        record.save()
                    elif is_checked and record.checked_by is None:
                        record.checked_by = request.user
                        record.checked_at = timezone.now()
                        record.save()

        messages.success(request, "Medication sheet saved.")
        return redirect('medication_sheet')

    existing_checks = MedicationCheck.objects.filter(
        bed__ward=assigned_ward, date__in=week_dates
    )
    check_map = {}
    for c in existing_checks:
        check_map[(c.bed_id, c.date, c.time_slot)] = c.is_given

    slot_field_map = {
        'morning': 'medication_morning',
        'noon': 'medication_afternoon',
        'evening': 'medication_evening',
    }

    grid = []
    for slot, slot_label in MedicationCheck.TIME_SLOT_CHOICES:
        slot_rows = []
        for bed in beds:
            active_admission = bed.admissions.filter(is_active=True).first()
            medication_text = ''
            if active_admission:
                medication_text = getattr(active_admission, slot_field_map[slot], '')

            row = {'bed': bed, 'medication': medication_text, 'cells': []}
            for date in week_dates:
                row['cells'].append({
                    'date': date,
                    'checkbox_name': f"check_{bed.id}_{date.isoformat()}_{slot}",
                    'checked': check_map.get((bed.id, date, slot), False),
                })
            slot_rows.append(row)
        grid.append({'slot': slot, 'label': slot_label, 'rows': slot_rows})

    return render(request, 'hospital/medication_sheet.html', {
        'assigned_ward': assigned_ward,
        'week_dates': week_dates,
        'grid': grid,
    })

@login_required
def meal_sheet(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if not assigned_ward:
        messages.error(request, "No ward assigned to your account.")
        return redirect('nurse_dashboard')

    today = timezone.now().date()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    beds = assigned_ward.beds.order_by('bed_number')

    if request.method == 'POST':
        for bed in beds:
            for date in week_dates:
                for slot, _ in MealCheck.MEAL_SLOT_CHOICES:
                    checkbox_name = f"meal_{bed.id}_{date.isoformat()}_{slot}"
                    is_checked = checkbox_name in request.POST

                    record, created = MealCheck.objects.get_or_create(
                        bed=bed, date=date, meal_slot=slot,
                        defaults={'is_served': is_checked}
                    )
                    if record.is_served != is_checked:
                        record.is_served = is_checked
                        record.checked_by = request.user if is_checked else None
                        record.checked_at = timezone.now() if is_checked else None
                        record.save()
                    elif is_checked and record.checked_by is None:
                        record.checked_by = request.user
                        record.checked_at = timezone.now()
                        record.save()

        messages.success(request, "Meal sheet saved.")
        return redirect('meal_sheet')

    existing_checks = MealCheck.objects.filter(bed__ward=assigned_ward, date__in=week_dates)
    check_map = {}
    for c in existing_checks:
        check_map[(c.bed_id, c.date, c.meal_slot)] = c.is_served

    grid = []
    for slot, slot_label in MealCheck.MEAL_SLOT_CHOICES:
        slot_rows = []
        for bed in beds:
            active_admission = bed.admissions.filter(is_active=True).first()
            diet_text = active_admission.get_diet_display() if active_admission else ''

            row = {'bed': bed, 'diet': diet_text, 'cells': []}
            for date in week_dates:
                row['cells'].append({
                    'date': date,
                    'checkbox_name': f"meal_{bed.id}_{date.isoformat()}_{slot}",
                    'checked': check_map.get((bed.id, date, slot), False),
                })
            slot_rows.append(row)
        grid.append({'slot': slot, 'label': slot_label, 'rows': slot_rows})

    return render(request, 'hospital/meal_sheet.html', {
        'assigned_ward': assigned_ward,
        'week_dates': week_dates,
        'grid': grid,
    })


@login_required
def search_patients(request):
    query = request.GET.get('q', '').strip()
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if not query:
        return JsonResponse({'results': []})

    admissions = Admission.objects.filter(
        is_active=True,
        patient__full_name__icontains=query
    ).select_related('patient', 'bed', 'bed__ward')

    if assigned_ward:
        admissions = admissions.filter(bed__ward=assigned_ward)

    admissions = admissions[:10]

    results = [
        {
            'name': a.patient.full_name,
            'ward': a.bed.ward.name,
            'bed_number': a.bed.bed_number,
            'url': f'/bed/{a.bed.id}/',
        }
        for a in admissions
    ]

    return JsonResponse({'results': results})


@login_required
def check_new_notifications(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if assigned_ward:
        latest = Notification.objects.filter(ward=assigned_ward).order_by('-id').first()
        count = Notification.objects.filter(ward=assigned_ward).order_by('-created_at')[:5].count()
    else:
        latest = Notification.objects.order_by('-id').first()
        count = Notification.objects.order_by('-created_at')[:5].count()

    return JsonResponse({
        'latest_id': latest.id if latest else 0,
        'count': count,
    })


@login_required
def update_medication(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)
    admission = bed.admissions.filter(is_active=True).first()

    if request.method == 'POST' and admission:
        admission.medication_morning = request.POST.get('medication_morning', '').strip()
        admission.medication_afternoon = request.POST.get('medication_afternoon', '').strip()
        admission.medication_evening = request.POST.get('medication_evening', '').strip()
        admission.save()
        messages.success(request, f"Medication schedule updated for {admission.patient.full_name}.")

    return redirect('bed_detail', bed_id=bed.id)


@login_required
def ward_beds(request, ward_id):
    ward = get_object_or_404(Ward, id=ward_id)
    beds = ward.beds.select_related().order_by('bed_number')
    for bed in beds:
        bed.active_admission = bed.admissions.filter(is_active=True).first()
    return render(request, 'hospital/ward_beds.html', {
        'ward': ward,
        'beds': beds,
        'all_wards': Ward.objects.all(),
    })


@login_required
def ward_beds_data(request, ward_id):
    ward = get_object_or_404(Ward, id=ward_id)
    beds = ward.beds.select_related().order_by('bed_number')

    beds_data = []
    for bed in beds:
        admission = bed.admissions.filter(is_active=True).first()
        beds_data.append({
            'id': bed.id,
            'bed_number': bed.bed_number,
            'status': bed.status,
            'status_display': bed.get_status_display(),
            'has_guardian_space': bed.has_guardian_space,
            'patient_age': admission.patient.age if admission else None,
            'patient_pin': admission.patient.patient_pin if admission else None,
            'medication_morning': admission.medication_morning if admission else '',
            'medication_afternoon': admission.medication_afternoon if admission else '',
            'medication_evening': admission.medication_evening if admission else '',
        })

    latest_notification = Notification.objects.filter(ward=ward).order_by('-id').first()

    return JsonResponse({
        'beds': beds_data,
        'latest_notification_id': latest_notification.id if latest_notification else 0,
    })


@login_required
def cleaner_dashboard_data(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if assigned_ward:
        beds_to_clean = Bed.objects.filter(status='cleaning', ward=assigned_ward)
        latest_notification = Notification.objects.filter(ward=assigned_ward).order_by('-id').first()
    else:
        beds_to_clean = Bed.objects.filter(status='cleaning')
        latest_notification = Notification.objects.order_by('-id').first()

    beds_data = [{'id': b.id, 'bed_number': b.bed_number, 'ward_name': b.ward.name} for b in beds_to_clean]

    return JsonResponse({
        'beds': beds_data,
        'latest_notification_id': latest_notification.id if latest_notification else 0,
    })


@login_required
def nurse_dashboard_data(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if not assigned_ward:
        return JsonResponse({'beds': [], 'latest_notification_id': 0})

    beds = assigned_ward.beds.select_related().order_by('bed_number')
    beds_data = []
    for bed in beds:
        admission = bed.admissions.filter(is_active=True).first()
        beds_data.append({
            'id': bed.id,
            'bed_number': bed.bed_number,
            'status': bed.status,
            'status_display': bed.get_status_display(),
            'has_guardian_space': bed.has_guardian_space,
            'patient_name': admission.patient.full_name if admission else None,
            'patient_age': admission.patient.age if admission else None,
            'patient_pin': admission.patient.patient_pin if admission else None,
            'medication_morning': admission.medication_morning if admission else '',
            'medication_afternoon': admission.medication_afternoon if admission else '',
            'medication_evening': admission.medication_evening if admission else '',
        })

    latest_notification = Notification.objects.filter(ward=assigned_ward).order_by('-id').first()

    return JsonResponse({
        'beds': beds_data,
        'latest_notification_id': latest_notification.id if latest_notification else 0,
    })


@login_required
def bed_detail(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)
    active_admission = bed.admissions.filter(is_active=True).first()
    form = None
    transfer_form = None

    if bed.status == 'available':
        form = AdmitPatientForm(ward=bed.ward)
    elif bed.status == 'occupied' and active_admission:
        transfer_form = TransferPatientForm(patient_gender=active_admission.patient.gender)

    bed_ward_map = {}
    if transfer_form:
        for b in transfer_form.fields['new_bed'].queryset:
            bed_ward_map.setdefault(str(b.ward_id), []).append({'id': b.id, 'label': b.bed_number})
    bed_ward_map_json = json.dumps(bed_ward_map)

    return render(request, 'hospital/bed_detail.html', {
        'bed': bed,
        'admission': active_admission,
        'form': form,
        'transfer_form': transfer_form,
        'bed_ward_map': bed_ward_map_json,
    })


@login_required
def admit_patient(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)

    if request.method == 'POST':
        form = AdmitPatientForm(request.POST, ward=bed.ward)
        if form.is_valid():
            patient = Patient.objects.create(
                full_name=form.cleaned_data['full_name'],
                gender=form.cleaned_data['gender'],
                date_of_birth=form.cleaned_data['date_of_birth'],
                contact_number=form.cleaned_data['contact_number'],
            )
            Admission.objects.create(
                patient=patient,
                bed=bed,
                admitted_by=request.user,
            )
            bed.status = 'occupied'
            bed.save()
            messages.success(request, f"{patient.full_name} admitted to {bed.bed_number}.")

            check_ward_capacity(bed.ward)
            check_forecast_alarm(bed.ward)

            return redirect('bed_detail', bed_id=bed.id)

    return redirect('bed_detail', bed_id=bed.id)


@login_required
def discharge_patient(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)
    admission = bed.admissions.filter(is_active=True).first()

    if request.method == 'POST' and admission:
        admission.discharge_date = timezone.now()
        admission.is_active = False
        admission.save()

        bed.status = 'cleaning'
        bed.save()

        messages.success(request, f"{admission.patient.full_name} discharged from {bed.bed_number}. Bed now requires cleaning.")

        Notification.objects.create(
            notification_type='cleaning_required',
            message=f"Bed {bed.bed_number} in {bed.ward.name} requires cleaning.",
            bed=bed,
            ward=bed.ward,
        )

    return redirect('bed_detail', bed_id=bed.id)


@login_required
def transfer_patient(request, bed_id):
    old_bed = get_object_or_404(Bed, id=bed_id)
    admission = old_bed.admissions.filter(is_active=True).first()

    if request.method == 'POST' and admission:
        form = TransferPatientForm(request.POST, patient_gender=admission.patient.gender)
        if form.is_valid():
            new_bed = form.cleaned_data['new_bed']

            admission.discharge_date = timezone.now()
            admission.is_active = False
            admission.save()

            Admission.objects.create(
                patient=admission.patient,
                bed=new_bed,
                admitted_by=request.user,
                medication_morning=admission.medication_morning,
                medication_afternoon=admission.medication_afternoon,
                medication_evening=admission.medication_evening,
            )

            old_bed.status = 'cleaning'
            old_bed.save()
            new_bed.status = 'occupied'
            new_bed.save()

            messages.success(request, f"{admission.patient.full_name} transferred from {old_bed.bed_number} to {new_bed.bed_number}.")

            check_ward_capacity(new_bed.ward)
            check_forecast_alarm(new_bed.ward)

            new_bed_ward_nurses = new_bed.ward.assigned_nurses.all()
            for nurse_profile in new_bed_ward_nurses:
                Notification.objects.create(
                    notification_type='bed_available',
                    message=f"Incoming patient: {admission.patient.full_name} transferred to {new_bed.bed_number} in {new_bed.ward.name}.",
                    bed=new_bed,
                    ward=new_bed.ward,
                )

            return redirect('bed_detail', bed_id=old_bed.id)

    return redirect('bed_detail', bed_id=old_bed.id)


@login_required
def mark_out_of_service(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)

    if request.method == 'POST' and bed.status == 'available':
        bed.status = 'out_of_service'
        bed.save()
        messages.success(request, f"Bed {bed.bed_number} marked as Out of Service.")

    return redirect('bed_detail', bed_id=bed.id)


@login_required
def restore_bed(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)

    if request.method == 'POST' and bed.status == 'out_of_service':
        bed.status = 'available'
        bed.save()
        messages.success(request, f"Bed {bed.bed_number} restored and is now Available.")

        Notification.objects.create(
            notification_type='bed_available',
            message=f"Bed {bed.bed_number} in {bed.ward.name} is now available (restored from Out of Service).",
            bed=bed,
            ward=bed.ward,
        )

    return redirect('bed_detail', bed_id=bed.id)


@login_required
def cleaner_dashboard(request):
    profile = request.user.profile
    assigned_ward = profile.assigned_ward

    if assigned_ward:
        beds_to_clean = Bed.objects.filter(status='cleaning', ward=assigned_ward)
        recent_notifications = Notification.objects.filter(ward=assigned_ward).order_by('-created_at')[:5]
    else:
        beds_to_clean = Bed.objects.filter(status='cleaning')
        recent_notifications = Notification.objects.order_by('-created_at')[:5]

    return render(request, 'hospital/cleaner_dashboard.html', {
        'assigned_ward': assigned_ward,
        'beds_to_clean': beds_to_clean,
        'notifications': recent_notifications,
    })


@login_required
def mark_bed_cleaned(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)

    if request.method == 'POST' and bed.status == 'cleaning':
        bed.status = 'available'
        bed.save()
        messages.success(request, f"Bed {bed.bed_number} marked as cleaned and is now available.")

        Notification.objects.create(
            notification_type='bed_available',
            message=f"Bed {bed.bed_number} in {bed.ward.name} is now available.",
            bed=bed,
            ward=bed.ward,
        )

    return redirect('cleaner_dashboard')