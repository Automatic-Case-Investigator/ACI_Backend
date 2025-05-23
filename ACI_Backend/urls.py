"""
URL configuration for ACI_Backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path("", views.home, name="home")
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path("", Home.as_view(), name="home")
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path("blog/", include("blog.urls"))
"""

from .objects.view_objects.reset_credentials_view import ResetCredentialsView
from rest_framework_simplejwt import views as jwt_views
from django.urls import path, include

urlpatterns = [
    path("token/", jwt_views.TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("reset_credentials/", ResetCredentialsView.as_view()),
    path("siem/", include("siem_endpoint.urls")),
    path("soar/", include("soar_endpoint.urls")),
    path("jobs/", include("jobs_endpoint.urls")),
    path("ai_backend/", include("ai_system_endpoint.urls")),
]
