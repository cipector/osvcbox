from django.contrib import admin

from .models import Client, Project, RegularPayment, WorkEntry, Workspace, WorkspaceMembership


admin.site.register(Workspace)
admin.site.register(WorkspaceMembership)
admin.site.register(Client)
admin.site.register(Project)
admin.site.register(RegularPayment)


@admin.register(WorkEntry)
class WorkEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "project", "start_time", "end_time", "deduct_lunch_break", "is_billable")
