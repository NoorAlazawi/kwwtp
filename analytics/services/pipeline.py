"""
خط المعالجة الكامل: قراءة → مؤشرات → تشخيص → إنذارات → فهارس.
يُنفَّذ كله ضمن معاملة واحدة لضمان الاتساق.
"""
from django.db import transaction
from .calculator import compute_metrics
from .diagnosis import run_diagnosis
from .alarms import generate_alarms
from .indices import compute_indices


@transaction.atomic
def process_reading(reading):
    """يعالج قراءة يومية بالكامل ويعيد (metric, scores)."""
    metric = compute_metrics(reading)
    run_diagnosis(reading, metric)
    crit, warn = generate_alarms(reading)
    scores = compute_indices(reading, alarms_counts=(crit, warn))
    return metric, scores
