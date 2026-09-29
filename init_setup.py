import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sysmonitor.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command

print("Running database migrations...")
call_command('makemigrations', 'dashboard')
call_command('migrate')

USERNAME = 'Avinash'
PASSWORD = 'Avinash@526'

print(f"Ensuring user '{USERNAME}' exists with specified credentials...")
user, created = User.objects.get_or_create(username=USERNAME)
user.set_password(PASSWORD)
user.is_superuser = True
user.is_staff = True
user.save()

if created:
    print(f"Created new superuser '{USERNAME}' with password successfully.")
else:
    print(f"Updated password for existing user '{USERNAME}' successfully.")

print("Setup completed successfully!")
