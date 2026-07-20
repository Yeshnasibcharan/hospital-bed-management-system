from django import forms
from .models import Patient, Bed, Ward


class AdmitPatientForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Patient full name'})
    )
    gender = forms.ChoiceField(
        choices=Patient.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'})
    )

    def __init__(self, *args, ward=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ward = ward
        if ward and ward.gender_restriction in ('male', 'female'):
            self.fields['gender'].widget = forms.HiddenInput()
            self.fields['gender'].initial = 'M' if ward.gender_restriction == 'male' else 'F'
        else:
            self.fields['gender'].required = True

    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if self.ward and self.ward.gender_restriction in ('male', 'female'):
            return 'M' if self.ward.gender_restriction == 'male' else 'F'
        if not gender:
            raise forms.ValidationError("Please select a gender.")
        return gender


class TransferPatientForm(forms.Form):
    new_ward = forms.ModelChoiceField(
        queryset=Ward.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_new_ward'}),
        label="Transfer to ward"
    )
    new_bed = forms.ModelChoiceField(
        queryset=Bed.objects.filter(status='available'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_new_bed'}),
        label="Transfer to bed"
    )

    def __init__(self, *args, patient_gender=None, **kwargs):
        super().__init__(*args, **kwargs)
        bed_qs = Bed.objects.filter(status='available')
        ward_qs = Ward.objects.all()

        if patient_gender:
            excluded_restriction = 'male' if patient_gender == 'F' else 'female'
            bed_qs = bed_qs.exclude(ward__gender_restriction=excluded_restriction)
            ward_qs = ward_qs.exclude(gender_restriction=excluded_restriction)

        self.fields['new_bed'].queryset = bed_qs.select_related('ward')
        self.fields['new_ward'].queryset = ward_qs.filter(id__in=bed_qs.values_list('ward_id', flat=True)).distinct()