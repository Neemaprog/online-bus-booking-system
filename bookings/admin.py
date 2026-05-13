from django.contrib import admin, messages
from .models import Booking, Passenger

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'trip', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'trip__route__origin', 'trip__route__destination')
    search_fields = ('booking_reference', 'user__username', 'trip__bus__company_name')
    date_hierarchy = 'created_at'
    raw_id_fields = ('trip',)

    # Ficha seats kwenye add mode
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is None:  # add mode
            fields = [f for f in fields if f != 'seats']
        return fields

    # Hii ina-save many-to-many baada ya ID
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:  # edit mode tu
            form.save_m2m()
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'seat', 'booking')
    search_fields = ('full_name', 'phone', 'booking__booking_reference')
    list_filter = ('booking__status',)
    raw_id_fields = ('seat', 'booking')
    
    def changelist_view(self, request, extra_context=None):
        # Clear seat blocking messages from admin
        storage = messages.get_messages(request)
        storage.used = True  # Mark all messages as used to clear them
        # Add back non-blocking messages
        for message in list(storage):
            if not any(keyword in str(message) for keyword in ['kimejiblok kwa sababu mda umekwisha', 'kimejiblok kwa sababu mda wa malipo umekwisha']):
                messages.info(request, str(message))
        return super().changelist_view(request, extra_context)