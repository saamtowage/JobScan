from unicodedata import name
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_endpoint, name="login"),
    path("logout", views.logout_endpoint, name="logout"),
    path("vessels", views.vessels, name="vessels"),
    path("vessels/<int:id>", views.edit_vessel, name="mod_vessel"),
    path("run-scan", views.run_scan, name="run_scan"),
] 