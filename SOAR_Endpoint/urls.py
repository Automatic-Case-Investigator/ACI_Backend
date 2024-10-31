from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("add_soar_info/", views.add_soar_info, name="add_soar_info"),
    path("set_soar_info/", views.set_soar_info, name="set_soar_info"),
    path("get_case/", views.get_case, name="get_case"),
    path("generate_tasks/", views.generate_tasks, name="get_case")
]