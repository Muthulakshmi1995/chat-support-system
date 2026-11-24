from django.urls import path
from . import views

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("tickets/new/", views.create_ticket, name="create_ticket"),
    path("tickets/<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/claim/<int:ticket_id>/", views.claim_ticket, name="claim_ticket"),
    path("staff/my-tickets/", views.my_tickets, name="my_tickets"),
    path("faq/ask/", views.get_faq_answer_view, name="get_faq_answer"),
]
