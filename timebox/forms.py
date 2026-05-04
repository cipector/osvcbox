from django import forms

from .models import Client, Project, RegularPayment, WorkEntry, Workspace


class WorkspaceSettingsForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "default_daily_hours", "default_hourly_rate_czk"]
        labels = {
            "name": "Název",
            "default_daily_hours": "Výchozí denní fond hodin",
            "default_hourly_rate_czk": "Výchozí hodinová sazba v Kč",
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "default_hourly_rate_czk"]
        labels = {
            "name": "Název",
            "default_hourly_rate_czk": "Výchozí hodinová sazba v Kč",
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["client", "name", "hourly_rate_czk", "is_active"]
        labels = {
            "client": "Klient",
            "name": "Název",
            "hourly_rate_czk": "Hodinová sazba v Kč",
            "is_active": "Aktivní",
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["client"].queryset = Client.objects.filter(workspace=workspace)

    def clean_client(self):
        client = self.cleaned_data["client"]
        if client.workspace_id != self.workspace.id:
            raise forms.ValidationError("Klient musí patřit do aktuálního pracovního prostoru.")
        return client


class WorkEntryForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ["date", "project", "start_time", "end_time", "deduct_lunch_break", "is_billable", "note"]
        labels = {
            "date": "Datum",
            "project": "Projekt",
            "start_time": "Začátek",
            "end_time": "Konec",
            "deduct_lunch_break": "Odečíst 30 minut na oběd",
            "is_billable": "Fakturovatelné",
            "note": "Poznámka",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["project"].queryset = Project.objects.filter(workspace=workspace, is_active=True)

    def clean_project(self):
        project = self.cleaned_data["project"]
        if project.workspace_id != self.workspace.id:
            raise forms.ValidationError("Projekt musí patřit do aktuálního pracovního prostoru.")
        return project

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "Konec musí být později než začátek.")
        if start_time and end_time and cleaned_data.get("deduct_lunch_break"):
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            if end_minutes - start_minutes <= 30:
                self.add_error("deduct_lunch_break", "Po odečtení oběda musí být délka záznamu větší než 0 hodin.")
        return cleaned_data


class RegularPaymentForm(forms.ModelForm):
    class Meta:
        model = RegularPayment
        fields = [
            "name",
            "amount_czk",
            "account_prefix",
            "account_number",
            "bank_code",
            "variable_symbol",
            "message",
            "reminder_day",
            "is_active",
        ]
        labels = {
            "name": "Název",
            "amount_czk": "Částka v Kč",
            "account_prefix": "Předčíslí účtu",
            "account_number": "Číslo účtu",
            "bank_code": "Kód banky",
            "variable_symbol": "Variabilní symbol",
            "message": "Zpráva pro příjemce",
            "reminder_day": "Den připomenutí v měsíci",
            "is_active": "Aktivní",
        }

    def clean_account_prefix(self):
        return _digits_only(self.cleaned_data.get("account_prefix", ""), "Předčíslí účtu")

    def clean_account_number(self):
        return _digits_only(self.cleaned_data["account_number"], "Číslo účtu")

    def clean_bank_code(self):
        bank_code = _digits_only(self.cleaned_data["bank_code"], "Kód banky")
        if len(bank_code) != 4:
            raise forms.ValidationError("Kód banky musí mít 4 číslice.")
        return bank_code

    def clean_variable_symbol(self):
        return _digits_only(self.cleaned_data.get("variable_symbol", ""), "Variabilní symbol")


def _digits_only(value, label):
    value = value.strip()
    if value and not value.isdigit():
        raise forms.ValidationError(f"{label} může obsahovat jen číslice.")
    return value
