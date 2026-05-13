from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import Trip, Seat


class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Inasubiri Malipo'),
        ('confirmed', 'Imethibitishwa'),
        ('cancelled', 'Imeghairiwa'),
        ('expired', 'Imeisha Muda'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name='bookings')
    booking_reference = models.CharField(max_length=20, unique=True, editable=False)
    seats = models.ManyToManyField(Seat, related_name='bookings', blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            # Generate reference kabla ya save
            self.booking_reference = f"BK-{timezone.now().strftime('%Y%m%d')}-{self.user.id}-{Booking.objects.count() + 1:04d}"
        
        super().save(*args, **kwargs)  # save kwanza ili kupata ID

        # Re-calculate price baada ya save
        if self.seats.exists():
            base = self.trip.base_price
            count = self.seats.count()
            surcharge = 0
            if self.trip.available_seats < 10:
                surcharge = base * 0.05
            new_price = (base + surcharge) * count
            if self.total_price != new_price:
                self.total_price = new_price
                super().save(update_fields=['total_price'])

    def __str__(self):
        return f"{self.booking_reference} - {self.user} ({self.trip})"

    class Meta:
        ordering = ['-created_at']


class Passenger(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
  
    seat = models.ForeignKey('core.Seat', on_delete=models.SET_NULL, null=True, related_name='bookings_passengers')  # ← ADD related_name tofauti
    # ... 
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    id_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.full_name} - Seat {self.seat.seat_number}"