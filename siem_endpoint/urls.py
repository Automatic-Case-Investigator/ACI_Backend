from django.urls import path
from .objects.view_objects.SIEM_info_view import (
    SIEMConfigFileDownloadView,
    SIEMInfoView,
)
from .objects.view_objects.SIEM_query_view import SIEMQueryView

urlpatterns = [
    path("siem_info/", SIEMInfoView.as_view()),
    path("config_file/", SIEMConfigFileDownloadView.as_view()),
    path("siem_query/", SIEMQueryView.as_view()),
]
