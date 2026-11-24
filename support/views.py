import json
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .ai import assign_priority, get_faq_answer
from .forms import RegisterForm, TicketForm, MessageForm, TicketStatusForm
from .models import Ticket, Message, StaffProfile

def register(request):
    if request.user.is_authenticated:
        return redirect("ticket_list")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("ticket_list")
    return render(request, "registration/register.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("ticket_list")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("ticket_list")
    return render(request, "registration/login.html", {"form": form})

@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return render(request, "registration/logout.html")

@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, "support/ticket_list.html", {"tickets": tickets})

@login_required
def create_ticket(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.user = request.user
        classification = assign_priority(ticket.subject, ticket.description)
        ticket.priority = classification["priority"]
        ticket.suggested_department = classification["department"]
        staff = StaffProfile.objects.filter(department=classification["department"]).order_by("id").first()
        ticket.assigned_to = staff
        ticket.save()
        messages.success(request, "Your ticket has been created.")
        return redirect("ticket_detail", ticket_id=ticket.pk)
    return render(request, "support/create_ticket.html", {"form": form})

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket.objects.select_related("user", "assigned_to__user"), pk=ticket_id)
    is_staff = request.user.is_superuser or StaffProfile.objects.filter(user=request.user).exists()
    if ticket.user_id != request.user.id and not is_staff:
        return HttpResponseForbidden("You cannot view this ticket.")
    if is_staff and not request.user.is_superuser:
        profile = request.user.staff_profile
        if ticket.assigned_to_id and ticket.assigned_to_id != profile.id:
            return HttpResponseForbidden("This ticket is assigned to another staff member.")
        if ticket.assigned_to_id is None and request.method == "GET":
            # Staff may inspect the queue ticket; claiming is a separate action.
            pass

    message_form = MessageForm(request.POST or None, prefix="message")
    status_form = TicketStatusForm(request.POST or None, instance=ticket, prefix="status")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "send_message" and message_form.is_valid():
            msg = message_form.save(commit=False)
            msg.ticket = ticket
            msg.user = request.user
            msg.save()
            return redirect("ticket_detail", ticket_id=ticket.pk)
        if action == "update_status" and is_staff and status_form.is_valid():
            status_form.save()
            messages.success(request, "Ticket status updated.")
            return redirect("ticket_detail", ticket_id=ticket.pk)
    return render(request, "support/ticket_detail.html", {
        "ticket": ticket, "messages_list": ticket.messages.select_related("user"),
        "message_form": message_form, "status_form": status_form, "is_staff": is_staff,
    })

@login_required
def staff_dashboard(request):
    if not (request.user.is_superuser or StaffProfile.objects.filter(user=request.user).exists()):
        return HttpResponseForbidden("Staff access required.")
    tickets = Ticket.objects.filter(assigned_to__isnull=True).select_related("user")
    return render(request, "support/staff_dashboard.html", {"tickets": tickets})

@login_required
@require_POST
def claim_ticket(request, ticket_id):
    if not (request.user.is_superuser or StaffProfile.objects.filter(user=request.user).exists()):
        return HttpResponseForbidden("Staff access required.")
    profile = StaffProfile.objects.filter(user=request.user).first()
    if profile is None:
        return HttpResponseForbidden("Create a StaffProfile before claiming tickets.")
    with transaction.atomic():
        ticket = Ticket.objects.select_for_update().filter(pk=ticket_id, assigned_to__isnull=True).first()
        if ticket:
            ticket.assigned_to = profile
            ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save(update_fields=["assigned_to", "status", "updated_at"])
            messages.success(request, f"Ticket #{ticket.pk} claimed.")
        else:
            messages.warning(request, "This ticket is no longer available.")
    return redirect("staff_dashboard")

@login_required
def my_tickets(request):
    if request.user.is_superuser:
        tickets = Ticket.objects.filter(assigned_to__isnull=False)
    else:
        profile = StaffProfile.objects.filter(user=request.user).first()
        if profile is None:
            return HttpResponseForbidden("Staff access required.")
        tickets = Ticket.objects.filter(assigned_to=profile)
    return render(request, "support/my_tickets.html", {"tickets": tickets})

@require_POST
def get_faq_answer_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Your session expired. Please sign in again."},
            status=401,
        )
    question = request.POST.get("question", "").strip()
    if not question and request.content_type == "application/json":
        try:
            question = json.loads(request.body).get("question", "").strip()
        except (json.JSONDecodeError, AttributeError):
            question = ""
    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)
    return JsonResponse({"answer": get_faq_answer(question)})
