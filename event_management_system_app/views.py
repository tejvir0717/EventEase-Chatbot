from django.shortcuts import render
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .models import Category, Event
from django.shortcuts import render, redirect
from django.urls import reverse


def delete_event(request, event_id):
	if request.method == 'POST':
		event = Event.objects.get(id=event_id)
		event.delete()
	return redirect(reverse('category_list'))

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def increment_participants(request, event_id):
    if request.method == 'POST':
        try:
            event = Event.objects.get(pk=event_id)
            event.participants += 1
            event.save()
            return JsonResponse({'status': 'success', 'participants': event.participants})
        except Event.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Event

def create_event(request):
    if request.method == 'POST':
        # Retrieve data from the POST request
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        priority = request.POST.get('priority')
        description = request.POST.get('description')
        location = request.POST.get('location')
        organizer = request.POST.get('organizer')
        
        # Retrieve the Category object
        category = get_object_or_404(Category, pk=category_id)
        
        # Create the Event object
        event = Event.objects.create(
            name=name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            description=description,
            location=location,
            organizer=organizer
        )
        # Redirect to the event list page
        return redirect('category_list')
    else:
        categories = Category.objects.all()
        return render(request, 'create_event.html', {'categories': categories})

def update_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        # Update event fields based on form data
        event.name = request.POST.get('name')
        event.category_id = request.POST.get('category')
        event.start_date = request.POST.get('start_date')
        event.end_date = request.POST.get('end_date')
        event.priority = request.POST.get('priority')
        event.description = request.POST.get('description')
        event.location = request.POST.get('location')
        event.organizer = request.POST.get('organizer')
        event.save()
        return redirect('category_list')
    else:
        categories = Category.objects.all()
        return render(request, 'update_event.html', {'event': event, 'categories': categories})
def category_list(request):
	categories = Category.objects.all()
	return render(request, 'category_list.html', {'categories': categories})

def create_category(request):
	if request.method == 'POST':
		name = request.POST.get('name')
		Category.objects.create(name=name)
		return redirect('category_list')
	return render(request, 'create_category.html')


def delete_category(request, category_id):
	category = Category.objects.get(pk=category_id)
	if category.event_set.exists():
		messages.error(
			request, "You cannot delete this category as it contains events.")
	else:
		category.delete()
		messages.success(request, "Category deleted successfully.")
	return redirect('category_list')

def category_events(request, category_id):
	category = get_object_or_404(Category, pk=category_id)
	events = category.event_set.all()
	return render(request, 'category_events.html', {'category': category, 'events': events})

def event_chart(request):
	categories = Category.objects.all()
	pending_counts = {}
	for category in categories:
		pending_counts[category.name] = Event.objects.filter(
			category=category,
			start_date__gt=timezone.now()
		).count()
	return render(request, 'event_chart.html', {'pending_counts': pending_counts})