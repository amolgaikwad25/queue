from django.db import models
from django.contrib.auth import get_user_model
from services.models import Service
from queue_system.models import Queue

User = get_user_model()


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('serve_next', 'Serve Next'),
        ('complete', 'Complete'),
        ('skip', 'Skip'),
        ('cancel', 'Cancel'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('reorder', 'Reorder'),
        ('priority', 'Priority'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    target_queue = models.ForeignKey(Queue, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} on {self.service} at {self.created_at}"
from django.db import models

# Create your models here.
