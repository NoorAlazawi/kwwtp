from django.contrib import admin
from .models import Plant, Clarifier, DailyReading

@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("name", "process", "num_clarifiers")

@admin.register(Clarifier)
class ClarifierAdmin(admin.ModelAdmin):
    list_display = ("plant", "number", "diameter_m", "surface_area_m2", "volume_m3", "is_active")
    list_filter = ("plant", "is_active")
    readonly_fields = ("surface_area_m2", "volume_m3")

@admin.register(DailyReading)
class DailyReadingAdmin(admin.ModelAdmin):
    list_display = ("clarifier", "date", "flow_q", "mlss", "sludge_blanket", "tss_out", "entered_by")
    list_filter = ("clarifier", "date")
    date_hierarchy = "date"
