from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class NotificationStatus(models.TextChoices):
    INIT = 'init', 'Init'
    QUEUED = 'queued', 'Queued'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class ChannelTypes(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = 'Channel Types'

    def __str__(self):
        return self.name


class Channels(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='channels')
    channel_types_id = models.ForeignKey(ChannelTypes, on_delete=models.CASCADE, related_name='channel_types_ids')
    config = models.CharField(max_length=255, blank=True, null=True,
                              help_text="Configuration URL for the notification service (e.g., Apprise URL)")
    template = models.TextField(help_text="Text/HTML template code for channel", blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # You could also add an is_public field if you want some channels to be shared between users
    is_public = models.BooleanField(default=False, help_text="If enabled, this channel can be used by all users")

    class Meta:
        verbose_name_plural = 'Channels'
        # Add unique constraint to prevent duplicate channels for the same user
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Notifications(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    # If you want to track which user the notification is intended for
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications',
                                 null=True, blank=True)
    body = models.TextField()
    extra = models.JSONField(default=dict, blank=True, null=True)
    channels_id = models.ForeignKey(Channels, on_delete=models.CASCADE, related_name='channels_ids')
    status = models.CharField(max_length=6, choices=NotificationStatus.choices,
                              default=NotificationStatus.INIT)
    details = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.body[:30]} - {self.sender.username}"