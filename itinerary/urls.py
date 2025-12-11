from django.urls import path
from . import views

urlpatterns = [
    path('generate-itinerary/', views.generate_itinerary),
]
