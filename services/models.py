from django.db import models

class Service(models.Model):
    SERVICE_TYPES = [
        ('hospital', 'Hospital'),
        ('ration_shop', 'Ration Shop'),
        ('bank', 'Bank'),
        ('government_office', 'Government Office'),
    ]

    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    location = models.CharField(max_length=200)
    num_counters = models.IntegerField(default=1)
    avg_service_time = models.IntegerField(default=5)  # in minutes
    # Track last issued token to guarantee sequential tokens per service
    last_token_number = models.IntegerField(default=0)
    # Allow pausing a service queue (no new serving will be assigned)
    paused = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.location}"
