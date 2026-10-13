from decimal import Decimal
from references.models import ParameterReference
from analytics.models import Diagnosis, DiagnosisRule

# نصوص افتراضية للسبب والإجراء لكل (مؤشر، حالة)
TEXTS = {
    "MLSS": {
        "normal":      ("تركيز العوالق في الخليط ضمن المدى المرجعي.", "متابعة روتينية لتركيز MLSS."),
        "underloaded": ("تركيز MLSS أقل من المرجع؛ كتلة حيوية منخفضة.", "مراجعة معدّل سحب الحمأة الزائدة (WAS) ونسبة الإرجاع."),
        "warning":     ("تركيز MLSS خارج المدى الأمثل.", "ضبط سحب الحمأة الزائدة ومراقبة الاتجاه."),
        "critical":    ("تركيز MLSS مرتفع جداً؛ إجهاد على الترسيب.", "مراجعة سحب الحمأة الزائدة وتحميل الحوض فوراً."),
    },
    "TSSe": {
        "normal":   ("جودة المياه الخارجة ضمن المدى المستهدف.", "متابعة روتينية لجودة المياه الخارجة."),
        "warning":  ("ارتفاع في المواد الصلبة الخارجة؛ احتمال تدهور أداء الترسيب.", "زيادة مراقبة TSS وفحص أداء الترسيب."),
        "critical": ("ارتفاع كبير في المواد الصلبة؛ انجراف صلب زائد.", "فحص تشغيل الحوض وطبقة الحمأة فوراً."),
    },
    "SVI": {
        "normal":      ("خصائص ترسيب الحمأة ضمن المدى المرجعي.", "متابعة روتينية لترسيب الحمأة."),
        "underloaded": ("SVI منخفض؛ حمأة كثيفة وسريعة الترسيب (احتمال Pin Floc).", "مراقبة عمر الحمأة وتركيز MLSS."),
        "warning":     ("تدهور قابلية ترسيب الحمأة؛ ميل نحو الانتفاخ.", "فحص قابلية الترسيب ومراقبة اتجاه SVI."),
        "critical":    ("ضعف ترسيب الحمأة؛ احتمال انتفاخ (Bulking).", "فحص فشل الترسيب وخصائص الحمأة مجهرياً."),
    },
    "SBD": {
        "normal":      ("تراكم طبقة الحمأة ضمن المدى المقبول.", "متابعة روتينية لطبقة الحمأة."),
        "underloaded": ("طبقة الحمأة رقيقة جداً (أقل من ٠٫٢٥ م).", "التحقق من معدّل سحب الحمأة وعدم الإفراط فيه."),
        "warning":     ("ارتفاع طبقة الحمأة؛ سحب غير كافٍ للحمأة.", "زيادة المراقبة والتحقق من أداء سحب الحمأة."),
        "critical":    ("تراكم مفرط لطبقة الحمأة؛ خطر انجراف صلب.", "فحص نظام سحب الحمأة وإزالة التراكم الزائد."),
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
        "normal":      ("نسبة الحمأة الراجعة ضمن المدى المرجعي.", "متابعة روتينية لـ RAS."),
        "underloaded": ("نسبة RAS أقل من المرجع؛ إرجاع غير كافٍ.", "زيادة تدفق الحمأة الراجعة ومراجعة مخزون الحمأة."),
        "warning":     ("نسبة RAS خارج المدى الأمثل.", "مراجعة ضبط تدفق RAS ومخزون الحمأة."),
        "critical":    ("نسبة RAS مرتفعة جداً؛ إعادة تدوير مفرطة.", "فحص تدفق RAS الزائد وتشغيل المضخات."),
    },
    "HRT": {
        "normal":   ("زمن المكوث ضمن المدى المرجعي.", "متابعة روتينية هيدروليكية."),
        "warning":  ("زمن المكوث خارج المدى الأمثل.", "التحقق من التدفق وتهيئة تشغيل الحوض."),
        "critical": ("زمن مكوث غير طبيعي؛ تدفق منخفض جداً أو إفراط هيدروليكي.", "التحقق من التدفق والحجم الفعّال وعدد الأحواض."),
    },
}


def classify(value: float, ref: ParameterReference) -> str:
    v = float(value)
    L, U = float(ref.lower_limit), float(ref.upper_limit)
    WU = float(ref.warning_upper)

    if ref.direction == ParameterReference.Direction.LOWER_BETTER:
        if v <= U:  return "normal"
        if v <= WU: return "warning"
        return "critical"

    if ref.code == "HRT":
        # <1.5 حرج، 1.5-2 تحذير، 2-6 طبيعي، 6-7 تحذير، ≥7 حرج
        if v < float(ref.warning_lower): return "critical"
        if v < L:  return "warning"
        if v <= U: return "normal"
        if v < float(ref.critical_lower): return "warning"
        return "critical"

    # مدى مستهدف ثنائي الطرف: critical_lower حدّ الحرج الأدنى، critical_upper حدّ الحرج الأعلى
    C_low, C_high = float(ref.critical_lower), float(ref.critical_upper)
    if v < L:
        return "critical" if v < C_low else "underloaded"
    if v <= U:
        return "normal"
    if v <= C_high:
        return "warning"
    return "critical"


SEVERITY = {"normal": "Low", "underloaded": "Medium", "warning": "Medium", "critical": "High"}


def get_rule(ref, status):
    # القاعدة المعدَّلة يدوياً (edited) تبقى كما هي؛ غيرها يتبع النص الافتراضي
    texts = TEXTS.get(ref.code, {})
    default_cause, default_action = texts.get(status, texts.get("warning", ("", "")))
    rule, created = DiagnosisRule.objects.get_or_create(
        parameter=ref, status=status,
        defaults={"cause": default_cause, "action": default_action},
    )
    if not rule.edited and (rule.cause != default_cause or rule.action != default_action):
        rule.cause, rule.action = default_cause, default_action
        rule.save(update_fields=["cause", "action"])
    return rule.cause, rule.action


def run_diagnosis(reading, metric):
    values = {
        "MLSS": reading.mlss,
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
