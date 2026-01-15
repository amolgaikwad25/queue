from django.db import models
from django.contrib.auth import get_user_model
from services.models import Service
from django.core.exceptions import ValidationError
from django.db import transaction

User = get_user_model()

class Queue(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('serving', 'Serving'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    token_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    joined_at = models.DateTimeField(auto_now_add=True)
    # When the service actually started serving this token
    service_start_time = models.DateTimeField(null=True, blank=True)
    # When the service finished serving this token
    service_end_time = models.DateTimeField(null=True, blank=True)
    # legacy timestamps kept for compatibility
    served_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    counter_number = models.IntegerField(null=True, blank=True)
    # Priority level: higher value means served earlier (for emergency/priority tokens)
    priority_level = models.IntegerField(default=0)
    # If token was skipped by admin, store the reason
    skip_reason = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('service', 'token_number')

    def __str__(self):
        return f"Token {self.token_number} - {self.user.username} at {self.service.name}"

    def clean(self):
        # Prevent more than one 'serving' token per service at the application level.
        if self.status == 'serving':
            qs = Queue.objects.filter(service=self.service, status='serving')
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('Only one token can be serving for a service at any time.')

    def save(self, *args, **kwargs):
        # Run validation within a transaction to reduce race windows.
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)
