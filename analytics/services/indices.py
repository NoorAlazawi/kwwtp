"""
حساب الفهارس المركّبة CHI / CSI / CRI (يقابل أوراق CHI, CSI, CRI في الملف).
"""
import statistics
from decimal import Decimal
from analytics.models import IndexScore, Diagnosis


def _status_map(reading):
    """قاموس {code: status} من تشخيصات القراءة."""
    return {d.parameter.code: d.status for d in reading.diagnoses.all()}


def compute_chi(reading):
    """مؤشر الصحة: TSSe 35% + SVI 30% + SBD 20% + SLR 15%. score: طبيعي100/تحذير60/حرج20."""
    st = _status_map(reading)
    weights = {"TSSe": 35, "SVI": 30, "SBD": 20, "SLR": 15}
    def score(s):
        return {"normal": 100, "underloaded": 80, "warning": 60, "critical": 20}.get(s, 0)
    total = sum(score(st.get(c, "critical")) * w / 100 for c, w in weights.items())
    status = ("Excellent" if total >= 85 else "Good" if total >= 70
              else "Warning" if total >= 50 else "Critical")
    return round(total, 1), status


def compute_cri(reading):
    """مؤشر المخاطر: TSSe30 + SBD15 + SOR25 + RAS10 + HRT20. risk: طبيعي0/تحذير50/حرج100."""
    st = _status_map(reading)
    weights = {"TSSe": 30, "SBD": 15, "SOR": 25, "RAS": 10, "HRT": 20}
    def risk(s):
        return {"normal": 0, "underloaded": 25, "warning": 50, "critical": 100}.get(s, 0)
    total = sum(risk(st.get(c, "critical")) * w / 100 for c, w in weights.items())
    level = ("Low" if total <= 20 else "Moderate" if total <= 40
             else "High" if total <= 70 else "Very High")
    return round(total, 1), level


def compute_csi(reading):
    """مؤشر الاستقرار: تباين CV آخر 7 أيام لـ SVI/SBD/SOR/HRT. يحتاج ≥ قراءتين."""
    from monitoring.models import DailyReading
    window = list(
        DailyReading.objects.filter(
            clarifier=reading.clarifier, date__lte=reading.date
        ).order_by("-date")[:7]
    )
    if len(window) < 2:
        return None, ""   # بيانات غير كافية

    def cv(vals):
        m = statistics.mean(vals)
        return (statistics.pstdev(vals) / m * 100) if m else 0

    def stability_score(cv_val):
        if cv_val <= 5:  return 100
        if cv_val <= 10: return 80
        if cv_val <= 20: return 60
        return 20

    svi = [float(r.metric.svi) for r in window if hasattr(r, "metric")]
    sbd = [float(r.sludge_blanket) for r in window]
    sor = [float(r.metric.sor) for r in window if hasattr(r, "metric")]
    hrt = [float(r.metric.hrt) for r in window if hasattr(r, "metric")]

    weights = [(svi, 35), (sbd, 30), (sor, 20), (hrt, 15)]
    total = sum(stability_score(cv(vals)) * w / 100 for vals, w in weights if len(vals) >= 2)
    status = ("Excellent" if total >= 85 else "Good" if total >= 70
              else "Warning" if total >= 50 else "Critical")
    return round(total, 1), status


def compute_indices(reading, alarms_counts=(0, 0)):
    """يحسب الفهارس الثلاثة + تقييم المشغّل ويخزّنها في IndexScore."""
    chi, chi_status = compute_chi(reading)
    cri, cri_level = compute_cri(reading)
    csi, csi_status = compute_csi(reading)

    # تقييم المشغّل: CHI40 + CSI30 + (100-CRI)20 + إدارة الإنذارات10
    crit, warn = alarms_counts
    alarm_mgmt = max(0, 100 - (crit * 25 + warn * 10))
    csi_val = csi if csi is not None else chi   # بديل عند نقص البيانات
    op = chi * 0.40 + csi_val * 0.30 + (100 - cri) * 0.20 + alarm_mgmt * 0.10
    op_rating = ("Excellent" if op >= 85 else "Good" if op >= 70
                 else "Fair" if op >= 50 else "Poor")

    score, _ = IndexScore.objects.update_or_create(
        reading=reading,
        defaults={
            "chi": Decimal(str(chi)), "chi_status": chi_status,
            "csi": (Decimal(str(csi)) if csi is not None else None), "csi_status": csi_status,
            "cri": Decimal(str(cri)), "cri_level": cri_level,
            "operator_score": Decimal(str(round(op, 1))), "operator_rating": op_rating,
        },
    )
    return score
