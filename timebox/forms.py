from django import forms

from .i18n import current_language, t
from .models import Client, Project, RegularPayment, WorkEntry, Workspace


class WorkspaceSettingsForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "default_daily_hours", "default_hourly_rate_czk"]

    def __init__(self, *args, **kwargs):
        language = kwargs.pop("language", current_language())
        super().__init__(*args, **kwargs)
        self.fields["name"].label = t(language, "forms_fields", "name")
        self.fields["default_daily_hours"].label = t(language, "forms_fields", "default_daily_hours")
        self.fields["default_hourly_rate_czk"].label = t(language, "forms_fields", "default_hourly_rate_czk")


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "default_hourly_rate_czk"]

    def __init__(self, *args, **kwargs):
        language = kwargs.pop("language", current_language())
        super().__init__(*args, **kwargs)
        self.fields["name"].label = t(language, "forms_fields", "name")
        self.fields["default_hourly_rate_czk"].label = t(language, "forms_fields", "default_hourly_rate_czk")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["client", "name", "hourly_rate_czk", "is_active"]

    def __init__(self, *args, workspace, **kwargs):
        language = kwargs.pop("language", current_language())
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["client"].queryset = Client.objects.filter(workspace=workspace)
        self.fields["client"].label = t(language, "forms_fields", "client")
        self.fields["name"].label = t(language, "forms_fields", "name")
        self.fields["hourly_rate_czk"].label = t(language, "forms_fields", "hourly_rate_czk")
        self.fields["is_active"].label = t(language, "forms_fields", "is_active")

    def clean_client(self):
        client = self.cleaned_data["client"]
        if client.workspace_id != self.workspace.id:
            raise forms.ValidationError(t(current_language(), "errors", "client_workspace"))
        return client


class WorkEntryForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ["date", "project", "start_time", "end_time", "deduct_lunch_break", "is_billable", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, workspace, **kwargs):
        language = kwargs.pop("language", current_language())
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["project"].queryset = Project.objects.filter(workspace=workspace, is_active=True)
        self.fields["date"].label = t(language, "forms_fields", "date")
        self.fields["project"].label = t(language, "forms_fields", "project")
        self.fields["start_time"].label = t(language, "forms_fields", "start_time")
        self.fields["end_time"].label = t(language, "forms_fields", "end_time")
        self.fields["deduct_lunch_break"].label = t(language, "forms_fields", "deduct_lunch_break")
        self.fields["is_billable"].label = t(language, "forms_fields", "is_billable")
        self.fields["note"].label = t(language, "forms_fields", "note")

    def clean_project(self):
        project = self.cleaned_data["project"]
        if project.workspace_id != self.workspace.id:
            raise forms.ValidationError(t(current_language(), "errors", "project_workspace"))
        return project

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", t(current_language(), "errors", "end_after_start"))
        if start_time and end_time and cleaned_data.get("deduct_lunch_break"):
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            if end_minutes - start_minutes <= 30:
                self.add_error("deduct_lunch_break", t(current_language(), "errors", "positive_duration"))
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
        labels = {}

    def __init__(self, *args, **kwargs):
        language = kwargs.pop("language", current_language())
        super().__init__(*args, **kwargs)
        for field_name in [
            "name",
            "amount_czk",
            "account_prefix",
            "account_number",
            "bank_code",
            "variable_symbol",
            "message",
            "reminder_day",
            "is_active",
        ]:
            self.fields[field_name].label = t(language, "forms_fields", field_name)

    def clean_account_prefix(self):
        return _digits_only(self.cleaned_data.get("account_prefix", ""), t(current_language(), "forms_fields", "account_prefix"))

    def clean_account_number(self):
        return _digits_only(self.cleaned_data["account_number"], t(current_language(), "forms_fields", "account_number"))

    def clean_bank_code(self):
        bank_code = _digits_only(self.cleaned_data["bank_code"], t(current_language(), "forms_fields", "bank_code"))
        if len(bank_code) != 4:
            raise forms.ValidationError(t(current_language(), "errors", "bank_code_length"))
        return bank_code

    def clean_variable_symbol(self):
        return _digits_only(self.cleaned_data.get("variable_symbol", ""), t(current_language(), "forms_fields", "variable_symbol"))


def _digits_only(value, label):
    value = value.strip()
    if value and not value.isdigit():
        raise forms.ValidationError(t(current_language(), "errors", "digits_only", label=label))
    return value
