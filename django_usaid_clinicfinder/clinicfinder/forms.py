import csv
from django import forms
from clinicfinder.tasks import pointofinterest_importer


class LocationsCSVUploader(forms.Form):
    csv = forms.FileField()

    def save(self):
        csv_data = list(csv.DictReader(self.cleaned_data["csv"]))
        pointofinterest_importer.delay(csv_data)
