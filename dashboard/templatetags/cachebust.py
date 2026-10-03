"""وسم قالب يضيف رقم إصدار للملف الثابت (بناءً على وقت تعديله) لتجاوز الكاش."""
import os
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    """يعيد رابط الملف الثابت مع ?v=mtime لإجبار المتصفّح على تحميل النسخة الجديدة."""
    url = static(path)
    # ابحث عن الملف الفعلي لقراءة وقت تعديله
    candidates = []
    if settings.STATICFILES_DIRS:
        candidates += [os.path.join(d, path) for d in settings.STATICFILES_DIRS]
    if getattr(settings, "STATIC_ROOT", None):
        candidates.append(os.path.join(settings.STATIC_ROOT, path))
    for fp in candidates:
        try:
            v = int(os.path.getmtime(fp))
            return f"{url}?v={v}"
        except OSError:
            continue
    return url
