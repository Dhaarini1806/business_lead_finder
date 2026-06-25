from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/<int:search_id>/", views.results_partial, name="results"),
    path("export/<int:search_id>/", views.export_excel, name="export"),
    path("history/", views.history, name="history"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
