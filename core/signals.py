# core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q
from .models import Seat, Trip

@receiver(post_save, sender='core.Seat')
def update_trip_available_seats(sender, instance, created, **kwargs):
    trip = instance.trip
    booked_or_blocked = trip.seats.filter(Q(is_booked=True) | Q(is_blocked=True)).count()
    trip.available_seats = trip.bus.total_seats - booked_or_blocked
    trip.save(update_fields=['available_seats'])

@receiver(post_delete, sender='core.Seat')
def update_trip_on_delete(sender, instance, **kwargs):
    trip = instance.trip
    booked_or_blocked = trip.seats.filter(Q(is_booked=True) | Q(is_blocked=True)).count()
    trip.available_seats = trip.bus.total_seats - booked_or_blocked
    trip.save(update_fields=['available_seats'])