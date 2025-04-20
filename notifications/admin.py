from django.core.exceptions import ValidationError
from .models import *
from django.db.models import Count
from import_export.admin import ImportExportModelAdmin
from admin_extra_buttons.api import ExtraButtonsMixin, button
from django.contrib import admin
from django.contrib import messages
from .forms import ChannelsAdminForm


@admin.register(ChannelTypes)
class ChannelTypesAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super(ChannelTypesAdmin, self).get_queryset(request)
        return qs.annotate(channels_count=Count('channel_types_ids'))

    def channels_count(self, inst):
        return inst.channels_count

    channels_count.short_description = "Number of channels"

    list_display = ("name", "channels_count",)
    search_fields = ("name",)



@admin.register(Channels)
class ChannelsAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    form = ChannelsAdminForm  # Use our custom form for validation
    list_display = ("name", "user", "channel_types_id", "get_template", "is_public", "created_at")
    search_fields = ("name", "description", "user__username")
    list_filter = ("channel_types_id", "is_public", "user", "created_at")
    list_editable = ("channel_types_id", "is_public")
    list_display_links = ("name", "get_template",)
    readonly_fields = ('created_at',)

    fieldsets = (
        (None, {
            'fields': ('name', 'user', 'channel_types_id', 'config', 'description', 'is_public')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('template', 'created_at'),
        }),
    )

    def get_template(self, obj):
        if obj.template is None:
            return "Add Template"
        return "Update Template"

    get_template.short_description = 'Template'

    def save_model(self, request, obj, form, change):
        """
        Custom save_model to handle success messages and set current user if not specified
        """
        # If user is not set and this is a new channel, use current user
        if not obj.user_id and not change:
            obj.user = request.user

        super().save_model(request, obj, form, change)

        # Only show success message for new channels
        if not change:
            messages.success(request, f"Channel '{obj.name}' created successfully!")

    def get_queryset(self, request):
        """Limit regular users to see only their own channels or public channels"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(models.Q(user=request.user) | models.Q(is_public=True))


@admin.register(Notifications)
class NotificationsAdmin(ExtraButtonsMixin, ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ("id", "short_body", "channels_id", "sender", "recipient", "status", "created_at")
    search_fields = ("body", "sender__username", "recipient__username", "id")
    list_filter = ("status", "channels_id", "sender", "created_at")
    list_display_links = ("short_body",)

    def short_body(self, obj):
        return obj.body[:30] + "..." if len(obj.body) > 30 else obj.body

    short_body.short_description = "Message Content"

    @button(permission='notifications.delete_notifications',
            html_attrs={"type": "button", "class": "btn btn-warning"},
            label='Delete Failed Notifications',
            confirm="Are you sure you want to delete all failed notifications? This action cannot be undone.")
    def delete_all_failed_notification(self, request):
        """
        Delete all failed notifications
        """
        qs = self.get_filtered_queryset(request)
        failed_notifications = qs.filter(status='failed')
        if failed_notifications.exists():
            count = failed_notifications.count()
            failed_notifications.delete()
            self.message_user(request, f"{count} failed notifications have been deleted.")
        else:
            self.message_user(request, "No failed notifications to delete.", level=messages.WARNING)

    @button(permission='notifications.delete_notifications',
            html_attrs={"type": "button", "class": "btn btn-danger"},
            label='Delete All Notifications',
            confirm="Are you sure you want to delete ALL notifications? This action cannot be undone and will remove ALL notifications regardless of status.")
    def delete_all_notifications(self, request):
        """
        Delete all notifications that the user has access to
        """
        qs = self.get_filtered_queryset(request)
        if qs.exists():
            count = qs.count()
            qs.delete()
            self.message_user(request, f"All {count} notifications have been deleted.")
        else:
            self.message_user(request, "No notifications to delete.", level=messages.WARNING)

    @button(permission='notifications.delete_notifications',
            html_attrs={"type": "button", "class": "btn btn-info"},
            label='Delete Selected Notification',
            confirm="Are you sure you want to delete the selected notification(s)? This action cannot be undone.")
    def delete_selected_notification(self, request):
        """
        Delete selected notification(s)
        """
        selected = request.POST.getlist('_selected_action')
        if selected:
            # Make sure we only delete notifications the user has access to
            qs = self.get_filtered_queryset(request)
            notifications = qs.filter(id__in=selected)
            count = notifications.count()
            notifications.delete()
            self.message_user(request, f"{count} selected notification(s) have been deleted.")
        else:
            self.message_user(request, "No notifications were selected for deletion.", level=messages.WARNING)

    def get_filtered_queryset(self, request):
        """Get the queryset filtered by user permissions"""
        qs = Notifications.objects.all()
        # If superuser, return all notifications
        if request.user.is_superuser:
            return qs
        # Otherwise, return only notifications sent or received by this user,
        # or sent through channels owned by this user
        return qs.filter(
            models.Q(sender=request.user) |
            models.Q(recipient=request.user) |
            models.Q(channels_id__user=request.user)
        )

    def get_queryset(self, request):
        """Limit users to see only notifications they sent, received, or through their channels"""
        return self.get_filtered_queryset(request)

    def save_model(self, request, obj, form, change):
        """Set sender to current user if not specified"""
        if not obj.sender_id:
            obj.sender = request.user
        super().save_model(request, obj, form, change)