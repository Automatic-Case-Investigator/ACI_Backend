
from django.urls import path
from .objects.view_objects.SIEM_info_view import SIEMInfoView
from .objects.view_objects.SIEM_query_view import SIEMQueryView

urlpatterns = [
    path("siem_info/", SIEMInfoView.as_view()),
    path("siem_query/", SIEMQueryView.as_view()),
]