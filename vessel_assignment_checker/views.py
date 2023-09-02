from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.management import call_command
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
from .models import *

# Create your views here.

def index(request):
    vessels = Vessel.objects.all()
    return render(request, "vessel_assignment_checker/index.html", {
        "vessels": vessels
    })

def login_endpoint(request):
    if request.method == "POST":

        data = json.loads(request.body)
        # Attempt to sign user in
        username = data.get("username")
        password = data.get("password")
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return JsonResponse({"message":"Logged in", "status":200}, status=200)
        else:
            return JsonResponse({"message":"Invalid credentials", "status":403}, status=403)
        
def logout_endpoint(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def edit_vessel(request, id):
    vessel = Vessel.objects.get(id=id)
    if request.method == "DELETE":
        vessel.delete()
        return JsonResponse({"message":"deleted", "status":200}, status=200)

def vessels(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data["vesselName"].upper()
        vessel = Vessel(name=name)
        vessel.save()
        return JsonResponse({"message":"Vessel added", "vessel":vessel.serialize(), "status":200}, status=200)
    
@login_required
def run_scan(request):
    call_command("scan")
    return JsonResponse({"message":"Scan running... Check email soon."}, status=200)