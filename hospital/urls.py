from django.urls import path
from . import views

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard-data/', views.admin_dashboard_data, name='admin_dashboard_data'),
    path('nurse-dashboard/', views.nurse_dashboard, name='nurse_dashboard'),
    path('nurse-dashboard-data/', views.nurse_dashboard_data, name='nurse_dashboard_data'),
    path('cleaner-dashboard/', views.cleaner_dashboard, name='cleaner_dashboard'),
    path('cleaner-dashboard-data/', views.cleaner_dashboard_data, name='cleaner_dashboard_data'),
    path('search-patients/', views.search_patients, name='search_patients'),
    path('ward/<int:ward_id>/beds/', views.ward_beds, name='ward_beds'),
    path('ward/<int:ward_id>/beds-data/', views.ward_beds_data, name='ward_beds_data'),
    path('bed/<int:bed_id>/', views.bed_detail, name='bed_detail'),
    path('bed/<int:bed_id>/admit/', views.admit_patient, name='admit_patient'),
    path('bed/<int:bed_id>/discharge/', views.discharge_patient, name='discharge_patient'),
    path('bed/<int:bed_id>/transfer/', views.transfer_patient, name='transfer_patient'),
    path('bed/<int:bed_id>/mark-cleaned/', views.mark_bed_cleaned, name='mark_bed_cleaned'),
    path('bed/<int:bed_id>/out-of-service/', views.mark_out_of_service, name='mark_out_of_service'),
    path('bed/<int:bed_id>/restore/', views.restore_bed, name='restore_bed'),
    path('bed/<int:bed_id>/update-medication/', views.update_medication, name='update_medication'),
    path('check-new-notifications/', views.check_new_notifications, name='check_new_notifications'),
    path('medication-sheet/', views.medication_sheet, name='medication_sheet'),
    path('export/bed-status/', views.export_bed_status_csv, name='export_bed_status_csv'),
    path('export/admission-history/', views.export_admission_history_csv, name='export_admission_history_csv'),
]