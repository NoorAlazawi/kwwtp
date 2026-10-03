"""
monitoring — المحطة، الأحواض، والقراءات اليومية.
هذا هو مصدر الإدخال (يقابل ورقة Raw data + plant information في الملف).
"""
import math
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Plant(models.Model):
    """محطة معالجة. تحمل الثوابت العامة (يقابل ورقة plant information)."""
    name = models.CharField("اسم المحطة", max_length=120, default="Karbala WWTP")
    process = models.CharField(
        "نوع المعالجة", max_length=120, default="Conventional Activated Sludge"
    )
    num_clarifiers = models.PositiveIntegerField("عدد الأحواض", default=8)
    clarifiers_in_service = models.PositiveIntegerField(
        "الأحواض العاملة", default=8,
        help_text="عدد الأحواض في الخدمة حالياً — يُقسَّم عليها التصريف الكلّي")

    class Meta:
        verbose_name = "محطة"
        verbose_name_plural = "المحطات"

    def __str__(self):
        return self.name


class Clarifier(models.Model):
    """حوض ترسيب دائري. المساحة والحجم يُحسبان تلقائياً من التصميم."""
    plant = models.ForeignKey(
        Plant, verbose_name="المحطة", on_delete=models.CASCADE, related_name="clarifiers"
    )
    number = models.PositiveIntegerField("رقم الحوض")
    shape = models.CharField("الشكل", max_length=20, default="circular")
    diameter_m = models.DecimalField(
        "القطر (م)", max_digits=6, decimal_places=2, default=Decimal("32")
    )
    side_water_depth = models.DecimalField(
        "عمق المياه الجانبي (م)", max_digits=5, decimal_places=2, default=Decimal("4")
    )
    # حقول مشتقّة (تُحسب عند الحفظ) — للقراءة فقط في الواجهة
    surface_area_m2 = models.DecimalField(
        "المساحة السطحية (م²)", max_digits=10, decimal_places=2,
        editable=False, null=True, blank=True,
    )
    volume_m3 = models.DecimalField(
        "الحجم التشغيلي (م³)", max_digits=12, decimal_places=2,
        editable=False, null=True, blank=True,
    )
    is_active = models.BooleanField("قيد الخدمة", default=True)
    color = models.CharField(
        "لون الحوض", max_length=9, blank=True, default="",
        help_text="لون مميّز لعناصر الحوض (hex). يُملأ تلقائياً إن تُرك فارغاً.")

    class Meta:
        verbose_name = "حوض"
        verbose_name_plural = "الأحواض"
        unique_together = ("plant", "number")   # لا تكرار لرقم الحوض في نفس المحطة
        ordering = ["plant", "number"]

    def save(self, *args, **kwargs):
        # A = π/4 × D²  ،  V = A × SWD   (كما في ورقة plant information)
        d = float(self.diameter_m)
        swd = float(self.side_water_depth)
        area = math.pi / 4 * d * d
        self.surface_area_m2 = round(Decimal(str(area)), 2)
        self.volume_m3 = round(Decimal(str(area * swd)), 2)
        super().save(*args, **kwargs)

    @property
    def total_area_m2(self) -> Decimal:
        """إجمالي مساحة كل الأحواض في المحطة (تُستخدم في SOR و SLR)."""
        return self.surface_area_m2 * self.plant.num_clarifiers

    @property
    def total_volume_m3(self) -> Decimal:
        """إجمالي الحجم (يُستخدم في HRT)."""
        return self.volume_m3 * self.plant.num_clarifiers

    # لوحة ألوان تلقائية للأحواض الثمانية
    PALETTE = [
        "#26c6da", "#2bb8a3", "#4a90d9", "#6d7ce8",
        "#9a7fe0", "#e8a94a", "#e8698c", "#3fb56b",
    ]

    @property
    def label(self) -> str:
        """اسم الحوض المختصر: ST-1 ... ST-8."""
        return f"ST-{self.number}"

    @property
    def ui_color(self) -> str:
        """لون عناصر الحوض — المخصّص إن وُجد، وإلا تلقائي من اللوحة."""
        if self.color:
            return self.color
        return self.PALETTE[(self.number - 1) % len(self.PALETTE)]

    def __str__(self):
        return f"{self.plant.name} — {self.label}"


class DailyReading(models.Model):
    """
    قراءة يوم واحد لحوض واحد (يقابل صفاً في ورقة Raw data).
    كل الحقول هنا مُدخلات خام؛ المؤشرات المشتقّة تُحسب في تطبيق analytics.
    """
    clarifier = models.ForeignKey(
        Clarifier, verbose_name="الحوض", on_delete=models.CASCADE, related_name="readings"
    )
    date = models.DateField("التاريخ")
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="أدخلها",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="readings",
    )

    # --- المدخلات (بنفس ترتيب أعمدة Raw data) ---
    flow_q = models.DecimalField(
        "التصريف الداخل Q (م³/يوم)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    ras_percent = models.DecimalField(
        "نسبة RAS (%)", max_digits=6, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        help_text="نسبة الحمأة الراجعة (عادةً 25–100%). لا تُدخل Qr المحسوب.",
    )
    was_percent = models.DecimalField(
        "نسبة WAS (%)", max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(15)],
        help_text="نسبة الحمأة المطروحة (عادةً 0.3–5%). لا تُدخل Qw المحسوب.",
    )
    mlss = models.DecimalField(
        "MLSS (mg/L)", max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    sv30 = models.DecimalField(
        "SV30 (mL/L)", max_digits=7, decimal_places=2, validators=[MinValueValidator(0)]
    )
    do = models.DecimalField(
        "الأكسجين الذائب DO (mg/L)", max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    temperature = models.DecimalField(
        "الحرارة (°م)", max_digits=5, decimal_places=2
    )
    sludge_blanket = models.DecimalField(
        "طبقة الحمأة (م)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0)]
    )
    tss_in = models.DecimalField("TSS داخل (mg/L)", max_digits=8, decimal_places=2)
    tss_out = models.DecimalField("TSS خارج (mg/L)", max_digits=8, decimal_places=2)
    cod_in = models.DecimalField("COD داخل (mg/L)", max_digits=8, decimal_places=2)
    cod_out = models.DecimalField("COD خارج (mg/L)", max_digits=8, decimal_places=2)
    bod_in = models.DecimalField("BOD داخل (mg/L)", max_digits=8, decimal_places=2)
    bod_out = models.DecimalField("BOD خارج (mg/L)", max_digits=8, decimal_places=2)
    ph = models.DecimalField(
        "pH", max_digits=4, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "قراءة يومية"
        verbose_name_plural = "القراءات اليومية"
        unique_together = ("clarifier", "date")   # يمنع تكرار يوم لنفس الحوض
        ordering = ["-date"]
        indexes = [models.Index(fields=["clarifier", "-date"])]

    def __str__(self):
        return f"{self.clarifier} — {self.date}"
