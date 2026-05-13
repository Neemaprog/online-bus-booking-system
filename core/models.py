from random import random
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from string import ascii_uppercase
from datetime import timedelta
from django.contrib.auth.models import User


class Place(models.Model):
    """Mikoa au vituo (Dar es Salaam, Dodoma, Arusha n.k.)"""
    name = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Places"


class Route(models.Model):
    """Njia kati ya maeneo mawili (Dar → Dodoma)"""
    origin = models.ForeignKey(Place, on_delete=models.PROTECT, related_name='routes_from')
    destination = models.ForeignKey(Place, on_delete=models.PROTECT, related_name='routes_to')
    distance_km = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    estimated_hours = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.5)])
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.origin} → {self.destination}"

    class Meta:
        unique_together = ['origin', 'destination']
        ordering = ['origin__name', 'destination__name']


class Bus(models.Model):
    # ... fields zingine ulizonazo ...
    merchant_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Namba ya Biashara (Merchant)")
    reference_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Kumbukumbu Namba (Reference)")
    # Optional: namba tofauti kwa kila network
    vodacom_merchant = models.CharField(max_length=20, blank=True, null=True)
    airtel_merchant = models.CharField(max_length=20, blank=True, null=True)
    halopesa_merchant = models.CharField(max_length=20, blank=True, null=True)
    mixx_merchant = models.CharField(max_length=20, blank=True, null=True)
    
    BUS_TYPES = (
        ('normal', 'Normal'),
        ('vip', 'VIP'),
        ('vvip', 'VVIP'),
    )

    plate_number = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=120)
    bus_type = models.CharField(max_length=20, choices=BUS_TYPES, default='normal')
    total_seats = models.PositiveIntegerField(validators=[MinValueValidator(10)])
    amenities = models.TextField(blank=True, help_text="WiFi, Charger, AC, TV, reclining seats etc.")
    is_active = models.BooleanField(default=True)

    # Intelligence: Multiplier ya bei kulingana na type ya basi
    @property
    def price_multiplier(self):
        multipliers = {
            'normal': 1.0,   # 100% (base)
            'vip': 1.4,      # +40%
            'vvip': 1.8      # +80%
        }
        return multipliers.get(self.bus_type, 1.0)

    def __str__(self):
        return f"{self.plate_number} - {self.company_name} ({self.get_bus_type_display()})"

    class Meta:
        ordering = ['company_name', 'plate_number']
    

class Trip(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('on_going', 'On Going'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name='trips')
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField(null=True, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1000)], null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    available_seats = models.PositiveIntegerField(default=0)

    def generate_seats(self):
        """Generate all seats automatically based on bus.total_seats"""
        if self.seats.exists():
            return

        seats_per_row = 4 if self.bus.bus_type == 'normal' else 5  # VIP/VVIP zina seats zaidi per row
        row_count = (self.bus.total_seats + seats_per_row - 1) // seats_per_row
        seat_list = []

        for row_letter in ascii_uppercase:
            for col in range(1, seats_per_row + 1):
                if len(seat_list) >= self.bus.total_seats:
                    break
                seat_number = f"{row_letter}{col}"
                seat_list.append(Seat(
                    trip=self,
                    seat_number=seat_number,
                    is_booked=False,
                    is_blocked=False
                ))

        Seat.objects.bulk_create(seat_list)
        self.available_seats = self.bus.total_seats
        self.save(update_fields=['available_seats'])

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # Intelligence 1: Auto-set arrival_time kama haijaset
        if not self.arrival_time and self.route.estimated_hours:
            self.arrival_time = self.departure_time + timezone.timedelta(hours=self.route.estimated_hours)

        # Intelligence 2: Bei inategemea bus_type (auto-calculate kama haijaset)
        if is_new or not self.base_price:
            multiplier = self.bus.price_multiplier
            default_base = self.route.distance_km * 100 if self.route.distance_km else 30000
            self.base_price = default_base * multiplier

        super().save(*args, **kwargs)

        # Intelligence 3: Generate seats kwa trip mpya
        if is_new:
            self.generate_seats()

    def __str__(self):
        return f"{self.bus.plate_number} | {self.route} | {self.departure_time.date()}"

    class Meta:
        ordering = ['-departure_time']


class Seat(models.Model):
    """Viti vya basi kwa kila trip (kwa kufuatilia availability)"""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)  # A1, B12, C5 n.k.
    is_booked = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)   # Kwa temporary hold (intelligence baadaye)
    blocked_until = models.DateTimeField(null=True, blank=True)  # auto-unblock after 15 min
    class Meta:
        unique_together = ['trip', 'seat_number']

    def save(self, *args, **kwargs):
        if self.is_blocked and not self.blocked_until:
            self.blocked_until = timezone.now() + timedelta(minutes=3)
        super().save(*args, **kwargs)

    def is_available(self):
        if self.is_booked:
            return False
        if self.is_blocked and self.blocked_until and timezone.now() > self.blocked_until:
            self.is_blocked = False
            self.blocked_until = None
            self.save()
            return True
        return not self.is_blocked
    class Meta:
        unique_together = ['trip', 'seat_number']
        ordering = ['seat_number']

    def __str__(self):
        status = "Booked" if self.is_booked else "Available"
        if self.is_blocked:
            status = "Blocked"
        return f"{self.trip} - {self.seat_number} ({status})"
class Passenger(models.Model):
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='passengers')
    seat = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, related_name='core_passengers')
    # ... fields zingine ...
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=[('M', 'Mume'), ('F', 'Mwanamke')])
    age_group = models.CharField(max_length=20, choices=[('Adult', 'Mtu mzima'), ('Child', 'Mtoto')])
    id_type = models.CharField(max_length=50, blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=100, default='Tanzania')
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - Seat {self.seat.seat_number if self.seat else 'N/A'}"
class Booking(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    reference_number = models.CharField(max_length=20, unique=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Pending')

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import random
            from django.utils import timezone
            self.reference_number = f"BK-{timezone.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference_number