"""
محرّك التشخيص — يطبّق منطق ورقة Diagnosis:
يقارن كل مؤشر بحدوده في ParameterReference ويولّد الحالة + السبب + الإجراء.
"""
from decimal import Decimal
from references.models import ParameterReference
from analytics.models import Diagnosis, DiagnosisRule

# نصوص السبب والإجراء لكل مؤشر وحالة (مستخرجة ومختصرة من ورقة Diagnosis)
TEXTS = {
    "TSSe": {
        "normal":   ("جودة المياه الخارجة ضمن المدى المستهدف.", "متابعة روتينية لجودة المياه الخارجة."),
        "warning":  ("ارتفاع في المواد الصلبة الخارجة؛ احتمال تدهور أداء الترسيب.", "زيادة مراقبة TSS وفحص أداء الترسيب."),
        "critical": ("ارتفاع كبير في المواد الصلبة؛ انجراف صلب زائد.", "فحص تشغيل الحوض وطبقة الحمأة فوراً."),
    },
    "SVI": {
        "normal":   ("خصائص ترسيب الحمأة ضمن المدى المرجعي.", "متابعة روتينية لترسيب الحمأة."),
        "warning":  ("تدهور قابلية ترسيب الحمأة؛ ميل نحو الانتفاخ.", "فحص قابلية الترسيب ومراقبة اتجاه SVI."),
        "critical": ("ضعف ترسيب الحمأة؛ احتمال انتفاخ (Bulking).", "فحص فشل الترسيب وخصائص الحمأة مجهرياً."),
    },
    "SBD": {
        "normal":   ("تراكم طبقة الحمأة ضمن المدى المقبول.", "متابعة روتينية لطبقة الحمأة."),
        "warning":  ("ارتفاع طبقة الحمأة؛ سحب غير كافٍ للحمأة.", "زيادة المراقبة والتحقق من أداء سحب الحمأة."),
        "critical": ("تراكم مفرط لطبقة الحمأة؛ خطر انجراف صلب.", "فحص نظام سحب الحمأة وإزالة التراكم الزائد."),
    },
    "SOR": {
        "normal":      ("معدل الفيض السطحي ضمن المدى المرجعي.", "متابعة روتينية للتحميل الهيدروليكي."),
        "underloaded": ("التحميل الهيدروليكي أقل من المرجع؛ تدفق منخفض أو سعة زائدة.", "التحقق من التدفق وعدد الأحواض في الخدمة."),
        "warning":     ("ارتفاع التحميل الهيدروليكي؛ خطر انخفاض أداء الترسيب.", "مراقبة التحميل والتحقق من توزيع التدفق."),
        "critical":    ("تحميل هيدروليكي مرتفع؛ احتمال إفراط هيدروليكي.", "التحقق من التدفق والتوزيع فوراً."),
    },
    "SLR": {
        "normal":      ("التحميل الصلب ضمن المدى المرجعي.", "متابعة روتينية للتحميل الصلب."),
        "underloaded": ("التحميل الصلب أقل من المرجع.", "التحقق من TSS الداخل وتركيز RAS."),
        "warning":     ("ارتفاع التحميل الصلب؛ إجهاد متزايد على الحوض.", "مراقبة التحميل ومخزون الحمأة."),
        "critical":    ("تحميل صلب مرتفع؛ احتمال إفراط وانجراف صلب.", "فحص التحميل ومخزون الحمأة فوراً."),
    },
    "RAS": {
        "normal":   ("نسبة الحمأة الراجعة ضمن المدى المرجعي.", "متابعة روتينية لـ RAS."),
        "warning":  ("نسبة RAS خارج المدى الأمثل.", "مراجعة ضبط تدفق RAS ومخزون الحمأة."),
        "critical": ("نسبة RAS مرتفعة جداً؛ إعادة تدوير مفرطة.", "فحص تدفق RAS الزائد وتشغيل المضخات."),
    },
    "HRT": {
        "normal":   ("زمن المكوث ضمن المدى المرجعي.", "متابعة روتينية هيدروليكية."),
        "warning":  ("زمن المكوث خارج المدى الأمثل.", "التحقق من التدفق وتهيئة تشغيل الحوض."),
        "critical": ("زمن مكوث غير طبيعي؛ تدفق منخفض جداً أو إفراط هيدروليكي.", "التحقق من التدفق والحجم الفعّال وعدد الأحواض."),
    },
}


def classify(value: float, ref: ParameterReference) -> str:
    """يحدّد الحالة (normal/underloaded/warning/critical) حسب اتجاه المؤشر."""
    v = float(value)
    L, U = float(ref.lower_limit), float(ref.upper_limit)
    WU, CL = float(ref.warning_upper), float(ref.critical_lower)

    if ref.direction == ParameterReference.Direction.LOWER_BETTER:
        if v <= U:  return "normal"
        if v <= WU: return "warning"
        return "critical"

    # target_range
    if ref.code == "HRT":
        # منطق خاص: <1.5 حرج، 1.5-2 تحذير، 2-4 طبيعي، 4-5 تحذير، >5 حرج
        if v < float(ref.warning_lower): return "critical"
        if v < L:  return "warning"
        if v <= U: return "normal"
        if v < float(ref.critical_lower): return "warning"
        return "critical"

    if v < L:  return "underloaded"
    if v <= U: return "normal"
    if v < CL: return "warning"
    return "critical"


SEVERITY = {"normal": "Low", "underloaded": "Low", "warning": "Medium", "critical": "High"}


def get_rule(ref, status):
    """يُرجع (السبب، الإجراء) من قاعدة التشخيص القابلة للتعديل.
    إن لم توجد القاعدة بعد، تُنشأ من النصوص الافتراضية (TEXTS) ثم تُحفظ — فتصبح قابلة للتعديل.
    القواعد المعدَّلة يدوياً (edited=True) لا تُستبدَل أبداً بالنصوص الافتراضية.
    """
    texts = TEXTS.get(ref.code, {})
    default_cause, default_action = texts.get(status, texts.get("warning", ("", "")))
    rule, created = DiagnosisRule.objects.get_or_create(
        parameter=ref, status=status,
        defaults={"cause": default_cause, "action": default_action},
    )
    if not rule.edited and (rule.cause != default_cause or rule.action != default_action):
        # تحديث النص الافتراضي ما لم يُعدَّل يدوياً
        rule.cause, rule.action = default_cause, default_action
        rule.save(update_fields=["cause", "action"])
    return rule.cause, rule.action


def run_diagnosis(reading, metric):
    """ينشئ تشخيصاً لكل مؤشر من المؤشرات السبعة."""
    # ربط كل رمز بقيمته الفعلية لهذه القراءة
    values = {
        "TSSe": reading.tss_out,
        "SVI": metric.svi,
        "SBD": reading.sludge_blanket,
        "SOR": metric.sor,
        "SLR": metric.slr,
        "RAS": reading.ras_percent,
        "HRT": metric.hrt,
    }
    results = []
    for code, value in values.items():
        ref = ParameterReference.objects.get(code=code)
        status = classify(value, ref)
        # النص من قاعدة التشخيص القابلة للتعديل (تُنشأ من TEXTS أول مرة)
        cause, action = get_rule(ref, status)
        diag, _ = Diagnosis.objects.update_or_create(
            reading=reading, parameter=ref,
            defaults={
                "value": Decimal(str(round(float(value), 3))),
                "status": status,
                "severity": SEVERITY[status],
                "cause": cause,
                "action": action,
                "priority": SEVERITY[status],
            },
        )
        results.append(diag)
    return results
