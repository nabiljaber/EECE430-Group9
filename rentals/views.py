from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Car
from .forms import CarForm, BookingForm


def home(request):
    cars = Car.objects.filter(available=True).order_by('-created_at')[:8]
    return render(request, 'home.html', {'cars': cars})

def car_list(request):
    qs = Car.objects.filter(available=True).order_by('-created_at')
    q = request.GET.get('q',''); t = request.GET.get('type','')
    if q: qs = qs.filter(title__icontains=q)
    if t: qs = qs.filter(car_type=t)
    return render(request, 'rentals/car_list.html', {'cars': qs, 'q': q, 'type': t})

def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    form = BookingForm()
    return render(request, 'rentals/car_detail.html', {'car': car, 'form': form})

@login_required
def add_car(request):
    form = CarForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('car_list')
    return render(request, 'rentals/car_form.html', {'form': form})

@login_required
def create_booking(request, pk):
    car = get_object_or_404(Car, pk=pk)
    form = BookingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.car = car
        booking.save()
        return redirect('car_detail', pk=car.pk)
    return render(request, 'rentals/car_detail.html', {'car': car, 'form': form})
