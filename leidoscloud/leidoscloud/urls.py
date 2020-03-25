"""leidoscloud URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("azure/", views.cloudsurfing, name="azure"),
    path("aws/", views.cloudsurfing, name="aws"),
    path("google/", views.cloudsurfing, name="google"),
    path("cloudsurf/", views.cloudsurf, name="CloudSurf"),
    path("log/", views.full_log, name="log"),
    path("log/delete/", views.full_log, name="delete_log"),
    path("status.json", views.cloudsurfing_status, name="status"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("predictions/", views.prediction, name="predictions"),
]
