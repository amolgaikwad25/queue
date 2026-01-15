from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    uqid = models.CharField(max_length=20, unique=True, blank=True)
    # canonical phone field (store exactly 10 digits, no country code)
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    sms_opt_in = models.BooleanField(default=True)

    # Backwards-compatibility property for code that may still reference `phone`.
    @property
    def phone(self):
        return self.phone_number

    def save(self, *args, **kwargs):
        if not self.uqid:
            # Generate UQID like UQID2026-000123
            import random
            year = 2026
            unique_id = str(random.randint(100000, 999999))  # 6 digit random number
            self.uqid = f"UQID{year}-{unique_id}"
        super().save(*args, **kwargs)
