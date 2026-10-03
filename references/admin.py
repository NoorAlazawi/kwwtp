from django.contrib import admin
from .models import ParameterReference

@admin.register(ParameterReference)
class ParameterReferenceAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ar", "unit", "direction",
                    "lower_limit", "upper_limit", "warning_upper", "critical_lower")
    search_fields = ("code", "name_ar", "name_en")
    list_filter = ("direction", "functional_area")
