from django.core.management.base import BaseCommand
from monitoring.models import DailyReading
from analytics.services.pipeline import process_reading


class Command(BaseCommand):
    help = "إعادة حساب المقاييس والتشخيص والإنذارات والفهارس لكل القراءات المخزّنة"

    def handle(self, *args, **options):
        qs = DailyReading.objects.select_related("clarifier").order_by("clarifier__number", "date")
        total = qs.count()
        for reading in qs:
            process_reading(reading)
        self.stdout.write(self.style.SUCCESS(f"تمت إعادة معالجة {total} قراءة."))
