"""
analytics — المخرجات المحسوبة من كل قراءة يومية:
المؤشرات المشتقّة (Metric) · التشخيص (Diagnosis) · الفهارس (IndexScore) · الإنذارات (Alarm).
"""
from django.db import models
from django.conf import settings


class Metric(models.Model):
    """المؤشرات المشتقّة لقراءة واحدة (يقابل ورقة Calculation)."""
    reading = models.OneToOneField(
        "monitoring.DailyReading", verbose_name="القراءة",
        on_delete=models.CASCADE, related_name="metric",
    )
    qr_ras = models.DecimalField("RAS (م³/يوم)", max_digits=14, decimal_places=2)
    qw_was = models.DecimalField("WAS (م³/يوم)", max_digits=14, decimal_places=2)
    svi = models.DecimalField("SVI (mL/g)", max_digits=12, decimal_places=2)
    sor = models.DecimalField("SOR (م³/م²·يوم)", max_digits=12, decimal_places=3)
    slr = models.DecimalField("SLR (kg/م²·ساعة)", max_digits=12, decimal_places=3)
    hrt = models.DecimalField("HRT (ساعة)", max_digits=12, decimal_places=3)
    tss_removal = models.DecimalField("إزالة TSS (%)", max_digits=6, decimal_places=2)
    cod_removal = models.DecimalField("إزالة COD (%)", max_digits=6, decimal_places=2)
    bod_removal = models.DecimalField("إزالة BOD (%)", max_digits=6, decimal_places=2)

    class Meta:
        verbose_name = "مؤشرات محسوبة"
        verbose_name_plural = "المؤشرات المحسوبة"

    def __str__(self):
        return f"مؤشرات {self.reading}"


class Diagnosis(models.Model):
    """تشخيص مؤشر واحد ليوم واحد (يقابل ورقة Diagnosis)."""

    class Status(models.TextChoices):
        NORMAL = "normal", "طبيعي"
        UNDERLOADED = "underloaded", "حمل منخفض"
        WARNING = "warning", "تحذير"
        CRITICAL = "critical", "حرج"

    reading = models.ForeignKey(
        "monitoring.DailyReading", verbose_name="القراءة",
        on_delete=models.CASCADE, related_name="diagnoses",
    )
    parameter = models.ForeignKey(
        "references.ParameterReference", verbose_name="المؤشر",
        on_delete=models.PROTECT, related_name="diagnoses",
    )
    value = models.DecimalField("القيمة", max_digits=12, decimal_places=3)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices)
    severity = models.CharField("الشدّة", max_length=10, blank=True)   # Low/Medium/High
    cause = models.TextField("السبب المحتمل", blank=True)
    action = models.TextField("الإجراء الموصى به", blank=True)
    priority = models.CharField("الأولوية", max_length=10, blank=True)

    class Meta:
        verbose_name = "تشخيص"
        verbose_name_plural = "التشخيصات"
        unique_together = ("reading", "parameter")

    def __str__(self):
        return f"{self.parameter.code}: {self.get_status_display()} — {self.reading.date}"


class IndexScore(models.Model):
    """الفهارس المركّبة ليوم واحد (CHI / CSI / CRI + بطاقة المشغّل)."""
    reading = models.OneToOneField(
        "monitoring.DailyReading", verbose_name="القراءة",
        on_delete=models.CASCADE, related_name="scores",
    )
    chi = models.DecimalField("مؤشر الصحة CHI", max_digits=5, decimal_places=1)
    chi_status = models.CharField("حالة الصحة", max_length=20)
    csi = models.DecimalField(
        "مؤشر الاستقرار CSI", max_digits=5, decimal_places=1, null=True, blank=True
    )
    csi_status = models.CharField("حالة الاستقرار", max_length=20, blank=True)
    cri = models.DecimalField("مؤشر المخاطر CRI", max_digits=5, decimal_places=1)
    cri_level = models.CharField("مستوى المخاطر", max_length=20)
    operator_score = models.DecimalField(
        "تقييم المشغّل", max_digits=5, decimal_places=1, null=True, blank=True
    )
    operator_rating = models.CharField("تقدير الأداء", max_length=20, blank=True)

    class Meta:
        verbose_name = "فهرس أداء"
        verbose_name_plural = "فهارس الأداء"

    def __str__(self):
        return f"CHI={self.chi} / CRI={self.cri} — {self.reading.date}"


class Alarm(models.Model):
    """إنذار ذكي (يقابل ورقة Smart Alarm System) — فعلي أو استباقي (تنبؤ)."""

    class Level(models.TextChoices):
        WARNING = "warning", "تحذير"
        CRITICAL = "critical", "حرج"

    reading = models.ForeignKey(
        "monitoring.DailyReading", verbose_name="القراءة",
        on_delete=models.CASCADE, related_name="alarms",
    )
    parameter = models.ForeignKey(
        "references.ParameterReference", verbose_name="المؤشر",
        on_delete=models.PROTECT, related_name="alarms",
    )
    alarm_code = models.CharField("رمز الإنذار", max_length=12)   # AL001...
    level = models.CharField("المستوى", max_length=10, choices=Level.choices)
    value = models.DecimalField("القيمة", max_digits=12, decimal_places=3)
    message = models.TextField("الرسالة", blank=True)
    action = models.TextField("الإجراء", blank=True)
    is_predicted = models.BooleanField("استباقي (تنبؤ)", default=False)
    acknowledged = models.BooleanField("تم الاطّلاع", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إنذار"
        verbose_name_plural = "الإنذارات"
        ordering = ["-created_at", "level"]

    def __str__(self):
        kind = "استباقي" if self.is_predicted else "فعلي"
        return f"[{self.get_level_display()}·{kind}] {self.parameter.code} — {self.reading.date}"


class DiagnosisRule(models.Model):
    """قاعدة تشخيص قابلة للتعديل: نص السبب + الإجراء (التنبيه/التوصية) لكل (مؤشر، حالة).
    تُخزَّن حسب المؤشر وحالته — فإذا تكرّرت نفس الحالة مستقبلاً تُعرض نفس النصوص المعدَّلة.
    """
    parameter = models.ForeignKey(
        "references.ParameterReference", verbose_name="المؤشر",
        on_delete=models.CASCADE, related_name="rules",
    )
    status = models.CharField("الحالة", max_length=20)   # normal/underloaded/warning/critical
    cause = models.TextField("السبب المحتمل", blank=True)
    action = models.TextField("الإجراء / التوصية", blank=True)
    edited = models.BooleanField("عُدّلت يدوياً", default=False)
    times_confirmed = models.PositiveIntegerField("مرّات التأكيد (تغذية رجعية)", default=0)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="عدّلها",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="diag_rules",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "قاعدة تشخيص"
        verbose_name_plural = "قواعد التشخيص"
        unique_together = ("parameter", "status")

    def __str__(self):
        return f"{self.parameter.code}·{self.status}"


class Recommendation(models.Model):
    """توصية تشغيلية قابلة للتعديل والإضافة من المشغّل (لكل حوض)."""
    clarifier = models.ForeignKey(
        "monitoring.Clarifier", verbose_name="الحوض",
        on_delete=models.CASCADE, related_name="recommendations",
    )
    date = models.DateField("تاريخ القراءة", null=True, blank=True,
                            help_text="التوصية تخصّ هذا اليوم فقط")
    text = models.CharField("نص التوصية", max_length=300)
    done = models.BooleanField("منفّذة", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="أضافها",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "توصية"
        verbose_name_plural = "التوصيات"
        ordering = ["done", "-created_at"]

    def __str__(self):
        return f"{self.clarifier.label}: {self.text[:40]}"
