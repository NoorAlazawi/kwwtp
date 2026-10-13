from django.db import models


class ParameterReference(models.Model):
    """حدود مؤشر واحد: طبيعي / تحذير / حرج، ومصدره العلمي."""

    class Direction(models.TextChoices):
        LOWER_BETTER = "lower_better", "الأقل أفضل"   # مثل TSSe و SBD
        TARGET_RANGE = "target_range", "مدى مستهدف"    # مثل SVI و SOR و HRT

    code = models.CharField("الرمز", max_length=10, unique=True)   # TSSe, SVI, SBD...
    name_ar = models.CharField("الاسم بالعربية", max_length=120)
    name_en = models.CharField("الاسم بالإنجليزية", max_length=120)
    unit = models.CharField("الوحدة", max_length=20)
    category = models.CharField("الفئة", max_length=60, blank=True)
    functional_area = models.CharField("المجال الوظيفي", max_length=40, blank=True)

    lower_limit = models.DecimalField("الحد الأدنى الطبيعي", max_digits=10, decimal_places=3)
    upper_limit = models.DecimalField("الحد الأعلى الطبيعي", max_digits=10, decimal_places=3)
    warning_lower = models.DecimalField("تحذير أدنى", max_digits=10, decimal_places=3)
    warning_upper = models.DecimalField("تحذير أعلى", max_digits=10, decimal_places=3)
    critical_lower = models.DecimalField("حرج أدنى", max_digits=10, decimal_places=3)
    critical_upper = models.DecimalField("حرج أعلى", max_digits=10, decimal_places=3)

    direction = models.CharField(
        "الاتجاه", max_length=20, choices=Direction.choices
    )
    reference = models.CharField("المرجع العلمي", max_length=160, blank=True)
    importance = models.CharField("الأهمية", max_length=20, blank=True)
    normal_range_text = models.CharField("المدى الطبيعي (نص)", max_length=60, blank=True)

    class Meta:
        verbose_name = "حدّ مرجعي"
        verbose_name_plural = "قاعدة الحدود العلمية"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name_ar}"
