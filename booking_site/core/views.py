from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from .forms import BookingForm
from .models import Booking, BookingStatus, Room, RoomCategory
# Create your views here.

def room_list(request):
    rooms = Room.objects.select_related("category").order_by("number")

    q = request.GET.get("q", "").strip()
    cat = request.GET.get("cat", "").strip()

    if q:
        rooms = rooms.filter(number__icontains=q)
    if cat:
        rooms = rooms.filter(category_id=cat)

    categories = RoomCategory.objects.filter(is_active=True).order_by("name")
    ctx = {"rooms": rooms, "categories": categories, "q": q, "cat": cat}
    return render(request, "core/room_list.html", ctx)

def room_detail(request, pk: int):
    room = get_object_or_404(Room.objects.select_related("category"), pk=pk)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Увійдіть, щоб забронювати кімнату.")
            return redirect(reverse("core:room_detail", args=[room.pk]))

        instance = Booking(room=room, user=request.user)
        form = BookingForm(request.POST, instance=instance)

        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except (ValidationError, IntegrityError) as e:
                form.add_error(None, getattr(e, "message", str(e)))
            else:
                messages.success(request, "Бронювання створено! Очікує підтвердження.")
                return redirect("core:my_bookings")
    else:
        form = BookingForm()

    last_bookings = room.bookings.select_related("user").order_by("-created_at")[:5]
    ctx = {
        "room": room,
        "form": form,
        "last_bookings": last_bookings,
    }
    return render(request, "core/room_detail.html", ctx)
    
@login_required
def my_bookings(request):
    """Список бронювань поточного користувача"""
    bookings = (Booking.objects.select_related("room", "room__category").filter(user=request.user).order_by("-created_at"))
    return render(request, "core/my_bookings.html", {"bookings": bookings})

@login_required
def booking_cancel(request, pk: int):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if booking.status != BookingStatus.CANCELED:
        booking.status = BookingStatus.CANCELED
        booking.save()
        messages.info(request, "Бронювання скасовано.")
    return redirect("core:my_bookings")
