import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_queue.settings')
django.setup()

from services.models import Service

# Create sample services
services_data = [
    {'name': 'City Hospital', 'service_type': 'hospital', 'location': 'Downtown', 'num_counters': 3, 'avg_service_time': 15},
    {'name': 'Central Bank', 'service_type': 'bank', 'location': 'Main Branch', 'num_counters': 5, 'avg_service_time': 10},
    {'name': 'Ration Depot', 'service_type': 'ration_shop', 'location': 'Sector 5', 'num_counters': 2, 'avg_service_time': 20},
    {'name': 'District Office', 'service_type': 'government_office', 'location': 'Administrative Block', 'num_counters': 4, 'avg_service_time': 25},
]

for data in services_data:
    Service.objects.get_or_create(**data)

print("Sample services created successfully!")