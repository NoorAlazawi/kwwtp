"""
accounts — المستخدمون والأدوار.
نعرّف User مخصّصاً ليحمل الدور (مشغّل/مشرف/مدير) والمحطة والهاتف.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """مستخدم النظام. يرث كل حقول Django (username, password, email...)."""

    class Role(models.TextChoices):
        OPERATOR = "operator", "مشغّل"        # يُدخل البيانات ويرى لوحته
        SUPERVISOR = "supervisor", "مشرف"      # يرى الكل + يعدّل الحدود
        MANAGER = "manager", "مدير"            # تقارير + إدارة المستخدمين

    role = models.CharField(
        "الدور", max_length=20, choices=Role.choices, default=Role.OPERATOR
    )
    # المحطة التي يتبعها المستخدم (نص مرجعي لتفادي الاستيراد الدائري)
    plant = models.ForeignKey(
        "monitoring.Plant",
        verbose_name="المحطة",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    phone = models.CharField("الهاتف", max_length=20, blank=True)  # لتنبيهات SMS

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    # اختصارات مفيدة للصلاحيات في القوالب والـ views
    @property
    def is_supervisor(self) -> bool:
        return self.role in {self.Role.SUPERVISOR, self.Role.MANAGER}

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
