from django.urls import path
from .objects.view_objects.dashboard_view import DashboardSummaryView

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view()),
]
