"""يشغّل خط المعالجة تلقائياً عند حفظ قراءة يومية."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from monitoring.models import DailyReading
from analytics.services.pipeline import process_reading


@receiver(post_save, sender=DailyReading)
def on_reading_saved(sender, instance, **kwargs):
    process_reading(instance)
