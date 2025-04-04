
from django.urls import path
from .objects.view_objects.SIEM_info_view import SIEMInfoView

urlpatterns = [
    path("siem_info/", SIEMInfoView.as_view()),
]