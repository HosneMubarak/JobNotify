# jobs/management/commands/test_huey.py
from django.core.management.base import BaseCommand
from jobs.tasks import my_task, my_periodic_task


class Command(BaseCommand):
    help = 'Test Huey tasks'

    def handle(self, *args, **options):
        # Queue a regular task
        result = my_task('test_parameter')
        self.stdout.write(f"Task queued with result: {result}")

        # Run the periodic task manually
        my_periodic_task()
        self.stdout.write("Periodic task ran successfully")