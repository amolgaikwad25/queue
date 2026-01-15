from django.db import models
from django.conf import settings


class SMSLog(models.Model):
    """Record of automated SMS notifications (pre-existing event-based logs).

    Keeps the simple (queue_id, event_type) uniqueness to avoid duplicates
    for the same event that originating code may try to send.
    """
    EVENT_CHOICES = [
        ('token_created', 'Token Created'),
        ('token_next', 'Token Next'),
        ('token_serving', 'Token Serving'),
        ('token_skipped', 'Token Skipped'),
        ('token_cancelled', 'Token Cancelled'),
        ('token_completed', 'Token Completed'),
    ]

    queue_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    provider_id = models.CharField(max_length=200, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('queue_id', 'event_type')

    def __str__(self):
        return f"SMSLog(queue={self.queue_id}, event={self.event_type}, success={self.success})"


class AdminSMSLog(models.Model):
    """Record manual SMS messages sent by admins for a specific queue token.

    This stores a full audit trail for admin-triggered SMS messages.
    """
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    queue = models.ForeignKey('queue_system.Queue', null=True, blank=True, on_delete=models.SET_NULL)
    token_number = models.IntegerField(null=True, blank=True, db_index=True)
    phone_number = models.CharField(max_length=20)
    message = models.CharField(max_length=160)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    provider_id = models.CharField(max_length=200, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"AdminSMSLog(queue={self.queue_id if hasattr(self,'queue_id') else self.queue}, token={self.token_number}, admin={self.admin})"
