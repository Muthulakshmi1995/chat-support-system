from django.contrib import admin
from .models import Ticket, Message, StaffProfile

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "status", "priority", "assigned_to", "created_at")
    list_filter = ("status", "priority", "suggested_department")
    search_fields = ("subject", "description", "user__username")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    search_fields = ("content",)

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department")
    list_filter = ("department",)
    search_fields = ("user__username",)
