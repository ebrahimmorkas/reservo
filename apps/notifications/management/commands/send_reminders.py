from django.core.management.base import BaseCommand

from apps.notifications.tasks import send_upcoming_reminders


class Command(BaseCommand):
    help = "Send reminder emails for upcoming bookings (cron alternative to Celery beat)."

    def handle(self, *args, **options):
        count = send_upcoming_reminders()
        self.stdout.write(self.style.SUCCESS(f"Queued {count} reminder(s)."))
