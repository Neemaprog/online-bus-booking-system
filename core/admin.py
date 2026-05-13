from django.contrib import admin, messages
from import_export.admin import ImportExportModelAdmin
from .models import Place, Route, Bus, Trip, Seat


@admin.register(Place)
class PlaceAdmin(ImportExportModelAdmin):
    
    list_display = ('id', 'name', 'region', 'is_active')
    list_filter = ('is_active', 'region')
    search_fields = ('name', 'region')
    list_per_page = 50  
    
    def changelist_view(self, request, extra_context=None):
       
        storage = messages.get_messages(request)
        storage.used = True  
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)


@admin.register(Route)
class RouteAdmin(ImportExportModelAdmin):
    list_display = ('__str__', 'distance_km', 'estimated_hours', 'is_active')
    list_filter = ('is_active', 'origin', 'destination')
    search_fields = ('origin__name', 'destination__name')
    list_per_page = 50
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)


@admin.register(Bus)
class BusAdmin(ImportExportModelAdmin):
    list_display = ('plate_number', 'company_name', 'bus_type', 'total_seats', 'is_active')
    list_filter = ('bus_type', 'company_name', 'is_active')
    search_fields = ('plate_number', 'company_name')
    list_per_page = 50
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)


@admin.register(Trip)
class TripAdmin(ImportExportModelAdmin):
    list_display = ('__str__', 'bus', 'route', 'departure_time', 'base_price', 'available_seats', 'status')
    list_filter = ('status', 'bus__bus_type', 'bus__company_name', 'route__origin', 'route__destination')
    search_fields = ('bus__plate_number', 'bus__company_name', 'route__origin__name')
    date_hierarchy = 'departure_time'
    list_per_page = 50
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)


@admin.register(Seat)
class SeatAdmin(ImportExportModelAdmin):
    list_display = ('seat_number', 'trip', 'is_booked', 'is_blocked')
    list_filter = ('is_booked', 'is_blocked', 'trip__bus__company_name')
    search_fields = ('seat_number', 'trip__bus__plate_number')
    list_per_page = 100
    list_editable = ('is_booked', 'is_blocked')  # Enable inline editing
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)