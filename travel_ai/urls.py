# travel_ai/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({"message": "Travel AI Backend is live!"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('itinerary.urls')),
    path('', root_view), 
]
