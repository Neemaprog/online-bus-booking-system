"""
URL configuration for busproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path
from django.views.generic import TemplateView
from . import views
from .views import BookingPreviewView, CompanyTripsView, PassengerDetailsView, PaymentCountdownView
from .views import SeatSelectionView
from django.urls import path
from .views import SearchResultsView, CompanyTripsView, SeatSelectionView, PassengerDetailsView



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('search/', TemplateView.as_view(template_name='search.html'), name='search'),
    path('search-results/', views.SearchResultsView.as_view(), name='search_results'),
    path('company-trips/', CompanyTripsView.as_view(), name='company_trips'),
    path('search-results/', views.SearchResultsView.as_view(), name='search_results'),
    path('seat-selection/<int:trip_id>/', SeatSelectionView.as_view(), name='seat_selection'),
    path('passenger-details/<int:trip_id>/', PassengerDetailsView.as_view(), name='passenger_details'),
   path('booking-preview/<int:trip_id>/', BookingPreviewView.as_view(), name='booking_preview'),
   path('payment-countdown/<int:trip_id>/', PaymentCountdownView.as_view(), name='payment_countdown'),
     
]
