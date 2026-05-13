from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import Route, Trip, Place, Seat, Passenger, Booking
from django.db.models import Q
from datetime import date, datetime, timedelta
from django.utils import timezone
import json
import random
from django.views import View
from django.contrib import messages

# SearchResultsView 
class SearchResultsView(TemplateView):
    template_name = 'search_results.html'

    def get(self, request):
        from_place = request.GET.get('from')
        to_place = request.GET.get('to')
        travel_date_str = request.GET.get('date')
        
        context = {
            'from_place': from_place,
            'to_place': to_place,
            'travel_date': travel_date_str,
            'travel_date_obj': date.fromisoformat(travel_date_str) if travel_date_str else None,
            'companies': [],
            'num_companies': 0,
        }

        if from_place and to_place and travel_date_str:
            route = Route.objects.filter(
                origin__name__iexact=from_place,
                destination__name__iexact=to_place,
                is_active=True
            ).first()

            if route:
                trips = Trip.objects.filter(
                    route=route,
                    status='scheduled',
                    available_seats__gt=0,
                    departure_time__date=context['travel_date_obj']
                ).select_related('bus')

                company_set = set()
                for trip in trips:
                    company_set.add(trip.bus.company_name)

                context['companies'] = sorted(list(company_set))
                context['num_companies'] = len(context['companies'])

                if not context['companies']:
                    context['no_results'] = True
                    context['message'] = f"Hakuna mabasi yanayopatikana kutoka {from_place} kwenda {to_place} tarehe {travel_date_str}."
            else:
                context['no_results'] = True
                context['message'] = f"Hakuna mabasi yaliyopatikana kutoka {from_place} kwenda {to_place}."

        else:
            context['error'] = "Tafadhali jaza maelezo yote kwenye form."

        return render(request, self.template_name, context)


# CompanyTripsView 
class CompanyTripsView(TemplateView):
    template_name = 'company_trips.html'

    def get(self, request):
        company_name = request.GET.get('company')
        from_place = request.GET.get('from')
        to_place = request.GET.get('to')
        travel_date = request.GET.get('date')
        time_filter = request.GET.get('time', 'all')

        context = {
            'trips': [],
            'num_trips': 0,
            'company_name': company_name,
            'from_place': from_place,
            'to_place': to_place,
            'travel_date': travel_date,
            'time_filter': time_filter,
        }

        if company_name and from_place and to_place and travel_date:
            trips = Trip.objects.filter(
                bus__company_name=company_name,
                route__origin__name=from_place,
                route__destination__name=to_place,
                departure_time__date=travel_date,
                status='scheduled',
                available_seats__gt=0
            )

            if time_filter == 'day':
                trips = trips.filter(departure_time__hour__gte=6, departure_time__hour__lt=18)
            elif time_filter == 'night':
                trips = trips.filter(Q(departure_time__hour__gte=18) | Q(departure_time__hour__lt=6))

            context['trips'] = trips.order_by('departure_time')
            context['num_trips'] = trips.count()

        return render(request, self.template_name, context)


# SeatSelectionView (updated – backend only)
class SeatSelectionView(TemplateView):
    template_name = 'seat_selection.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trip_id = self.kwargs['trip_id']
        trip = get_object_or_404(Trip, id=trip_id)
        context['trip'] = trip
        context['seats'] = trip.seats.all().order_by('seat_number')
        context['base_price'] = float(trip.base_price)

        selected_seats = self.request.session.get(f'selected_seats_{trip_id}', [])
        
        # Check and unblock expired seats
        current_time = timezone.now()
        valid_seats = []
        for seat_number in selected_seats:
            try:
                seat = Seat.objects.get(trip=trip, seat_number=seat_number)
                if seat.is_blocked and seat.blocked_until and current_time > seat.blocked_until:
                    # Seat expired, unblock it
                    seat.is_blocked = False
                    seat.blocked_until = None
                    seat.save()
                    messages.warning(self.request, f"Kiti {seat_number} kimejiblok kwa sababu mda umekwisha.")
                elif seat.is_blocked:
                    valid_seats.append(seat_number)
            except Seat.DoesNotExist:
                continue
        
        # Update session with only valid seats
        self.request.session[f'selected_seats_{trip_id}'] = valid_seats
        self.request.session.modified = True
        
        context['selected_seats'] = valid_seats
        context['total_price'] = len(valid_seats) * context['base_price']

        return context

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        action = request.POST.get('action')
        seat_number = request.POST.get('seat_number')

        if not seat_number:
            return render(request, self.template_name, self.get_context_data())

        seat = get_object_or_404(Seat, trip=trip, seat_number=seat_number)

        session_key = f'selected_seats_{trip_id}'
        selected_seats = request.session.get(session_key, [])

        if action == 'select':
            if seat.is_available():
                seat.is_blocked = True
                seat.blocked_until = timezone.now() + timedelta(minutes=3)
                seat.save()

                if seat_number not in selected_seats:
                    selected_seats.append(seat_number)
                    request.session[session_key] = selected_seats
                    request.session.modified = True

        elif action == 'unselect':
            if seat.is_blocked and not seat.is_booked:
                seat.is_blocked = False
                seat.blocked_until = None
                seat.save()

                if seat_number in selected_seats:
                    selected_seats.remove(seat_number)
                    request.session[session_key] = selected_seats
                    request.session.modified = True

        return render(request, self.template_name, self.get_context_data())


# PassengerDetailsView 
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from core.models import Trip, Seat  

class PassengerDetailsView(TemplateView):
    template_name = 'passenger_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trip_id = self.kwargs['trip_id']
        trip = get_object_or_404(Trip, id=trip_id)
        selected_seats = self.request.session.get(f'selected_seats_{trip_id}', [])
        context['trip'] = trip
        context['selected_seats'] = selected_seats
        context['total_price'] = len(selected_seats) * float(trip.base_price)
        context['seat_count'] = len(selected_seats)
        return context

    def post(self, request, trip_id):
        selected_seats = request.session.get(f'selected_seats_{trip_id}', [])
        if not selected_seats:
            messages.error(request, "Hakuna kiti kilichochaguliwa. Chagua kiti kwanza.")
            return redirect('seat_selection', trip_id=trip_id)

        # Save data kwa kila seat iliyochaguliwa
        passenger_data = {}
        for i, seat_number in enumerate(selected_seats, 1):
            passenger_data[f'passenger_{i}'] = {
                'seat': seat_number,
                'first_name': request.POST.get(f'passenger_{i}_first_name', 'N/A'),
                'last_name': request.POST.get(f'passenger_{i}_last_name', 'N/A'),
                'phone': request.POST.get(f'passenger_{i}_phone', 'N/A'),
                'gender': request.POST.get(f'passenger_{i}_gender', 'N/A'),
                'age_group': request.POST.get(f'passenger_{i}_age_group', 'N/A'),
                'id_type': request.POST.get(f'passenger_{i}_id_type', 'N/A'),
                'id_number': request.POST.get(f'passenger_{i}_id_number', 'N/A'),
                'nationality': request.POST.get(f'passenger_{i}_nationality', 'Tanzania'),
            }

        # Save kwenye session
        request.session['preview_passenger_data'] = passenger_data
        request.session['preview_seat_count'] = len(selected_seats)
        request.session['preview_total_price'] = len(selected_seats) * float(
            get_object_or_404(Trip, id=trip_id).base_price
        )
        request.session.modified = True

        # Redirect kwenye preview
        return redirect('booking_preview', trip_id=trip_id)


class BookingPreviewView(View):
    template_name = 'booking_preview.html'  # ← use better namespacing

    def dispatch(self, request, *args, **kwargs):
        trip_id = kwargs.get('trip_id')
        if not trip_id:
            return redirect('some-home-page')  # or raise 404

        self.trip = get_object_or_404(Trip, id=trip_id)
        self.selected_seats = request.session.get(f'selected_seats_{trip_id}', [])

        if not self.selected_seats:
            if request.method == 'POST':
                messages.error(request, "Hakuna kiti kilichochaguliwa. Chagua kiti kwanza.")
                return redirect('seat_selection', trip_id=trip_id)
            # For GET — we can still show preview with warning, or redirect
            # Here we allow showing empty preview → you decide

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Show the preview page (data from session)"""
        passenger_data = request.session.get('preview_passenger_data', {})
        seat_count = len(self.selected_seats)

        # Intelligent / automatic calculations
        base_total = seat_count * float(self.trip.base_price)
        # Example: future place for discount logic
        discount = 0
        if seat_count >= 4:
            discount = base_total * 0.05  # 5% group discount example
        total_after_discount = base_total - discount

        context = {
            'trip': self.trip,
            'selected_seats': self.selected_seats,
            'seat_count': seat_count,
            'base_total': base_total,
            'discount': discount,
            'total_price': total_after_discount,
            'passenger_data': passenger_data,
            'current_time': timezone.now(),
            # Future intelligent additions:
            # 'recommended_insurance': self.trip.recommend_insurance(),
            # 'estimated_boarding_time': self.trip.estimated_boarding(),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Save passenger info from the preview form to session
        Then redirect to GET (PRG pattern → prevents double submit on refresh)
        """
        if not self.selected_seats:
            messages.error(request, "Chagua viti tena.")
            return redirect('seat_selection', trip_id=self.trip.id)

        passenger_data = {}

        # Assuming form has fields like: passenger_1_first_name, passenger_2_phone, etc.
        for i in range(1, len(self.selected_seats) + 1):
            prefix = f'passenger_{i}_'
            passenger_data[f'passenger_{i}'] = {
                'seat': self.selected_seats[i-1],
                'first_name': request.POST.get(prefix + 'first_name', '').strip() or 'N/A',
                'last_name': request.POST.get(prefix + 'last_name', '').strip() or 'N/A',
                'phone': request.POST.get(prefix + 'phone', '').strip() or 'N/A',
                'gender': request.POST.get(prefix + 'gender', 'N/A'),
                'age_group': request.POST.get(prefix + 'age_group', 'N/A'),
                'id_type': request.POST.get(prefix + 'id_type', 'N/A'),
                'id_number': request.POST.get(prefix + 'id_number', 'N/A'),
                'nationality': request.POST.get(prefix + 'nationality', 'Tanzania'),  # intelligent default
            }

            # Small automatic intelligence examples:
            phone = passenger_data[f'passenger_{i}']['phone']
            if phone.startswith(('0', '+255')) and not passenger_data[f'passenger_{i}']['nationality']:
                passenger_data[f'passenger_{i}']['nationality'] = 'Tanzania'

        # Save to session
        request.session['preview_passenger_data'] = passenger_data
        request.session['preview_seat_count'] = len(self.selected_seats)
        request.session['preview_total_price'] = float(len(self.selected_seats) * self.trip.base_price)
        request.session.modified = True

        # Redirect to GET version of same page → shows updated preview
        return redirect('booking_preview', trip_id=self.trip.id)
class PaymentCountdownView(TemplateView):
    template_name = 'payment_countdown.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trip_id = self.kwargs['trip_id']
        trip = get_object_or_404(Trip, id=trip_id)
        bus = trip.bus  # basi husika

        selected_seats = self.request.session.get(f'selected_seats_{trip_id}', [])
        total_price = len(selected_seats) * float(trip.base_price)

        # Check if any seats have expired and unblock them
        self.unblock_expired_seats(trip_id, selected_seats)

        context.update({
            'trip': trip,
            'bus': bus,
            'total_price': total_price,
            'seat_count': len(selected_seats),
            # Namba dynamic kutoka basi
            'merchant_number': bus.merchant_number or '0090909',
            'reference_number': bus.reference_number or '9030211113870',
            'vodacom_merchant': bus.vodacom_merchant or 'VODA123',
            'airtel_merchant': bus.airtel_merchant or 'AIRTEL456',
            'halopesa_merchant': bus.halopesa_merchant or 'HALO789',
            'mixx_merchant': bus.mixx_merchant or 'MIXX000',
        })

        return context
    
    def unblock_expired_seats(self, trip_id, selected_seats):
        """Unblock seats whose blocking time has expired"""
        current_time = timezone.now()
        for seat_number in selected_seats:
            try:
                seat = Seat.objects.get(trip_id=trip_id, seat_number=seat_number)
                if seat.is_blocked and seat.blocked_until and current_time > seat.blocked_until:
                    seat.is_blocked = False
                    seat.blocked_until = None
                    seat.save()
                    messages.warning(self.request, f"Kiti {seat_number} kimejiblok kwa sababu mda wa malipo umekwisha.")
            except Seat.DoesNotExist:
                continue

    def post(self, request, trip_id):
    # Kama user anafikia payment na mda umekwisha, block seats
        selected_seats = request.session.get(f'selected_seats_{trip_id}', [])
        for seat_number in selected_seats:
         seat = get_object_or_404(Seat, trip_id=trip_id, seat_number=seat_number)
        if seat.is_blocked and seat.blocked_until < timezone.now():
            seat.is_blocked = False
            seat.blocked_until = None
            seat.is_booked = False
            seat.save()
            messages.warning(request, f"Kiti {seat_number} kimejiblok kwa sababu mda wa malipo umekwisha.")
        return redirect('seat_selection', trip_id=trip_id)