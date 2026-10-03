from django.contrib import admin
from .models import Metric, Diagnosis, IndexScore, Alarm

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("reading", "svi", "sor", "slr", "hrt", "tss_removal")

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("reading", "parameter", "value", "status", "severity", "priority")
    list_filter = ("status", "parameter")

@admin.register(IndexScore)
class IndexScoreAdmin(admin.ModelAdmin):
    list_display = ("reading", "chi", "chi_status", "csi", "cri", "cri_level", "operator_score")

@admin.register(Alarm)
class AlarmAdmin(admin.ModelAdmin):
    list_display = ("reading", "parameter", "level", "value", "is_predicted", "acknowledged")
    list_filter = ("level", "is_predicted", "acknowledged")
