#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_queue.settings')
django.setup()

from accounts.models import User

def update_admin():
    try:
        admin_user = User.objects.get(username='admin')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        print("Admin user updated with staff and superuser privileges")
    except User.DoesNotExist:
        print("Admin user not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    update_admin()