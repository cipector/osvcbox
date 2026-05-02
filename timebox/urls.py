from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("workspace/", views.workspace_settings, name="workspace_settings"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("regular-payments/", views.regular_payment_list, name="regular_payment_list"),
    path("regular-payments/new/", views.regular_payment_create, name="regular_payment_create"),
    path("regular-payments/<int:pk>/edit/", views.regular_payment_update, name="regular_payment_update"),
    path("work-entries/new/", views.work_entry_create, name="work_entry_create"),
    path("work-entries/<int:pk>/edit/", views.work_entry_update, name="work_entry_update"),
    path("work-entries/<int:pk>/delete/", views.work_entry_delete, name="work_entry_delete"),
    path("reports/work-entries/", views.work_entry_report, name="work_entry_report"),
]
