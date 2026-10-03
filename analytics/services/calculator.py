"""
حساب المؤشرات المشتقّة من قراءة يومية — يطبّق معادلات ورقة Calculation حرفياً.
"""
from decimal import Decimal
from analytics.models import Metric


def _d(x) -> Decimal:
    return Decimal(str(x))


def compute_metrics(reading) -> Metric:
    """يحسب SLR, SOR, HRT, SVI, ونسب الإزالة ويخزّنها في Metric.

    التصريف Q في القراءة هو نصيب الحوض الواحد مباشرةً (لكل حوض قراءاته الخاصة).
    تُطبّق المعادلات بمساحة وحجم الحوض الواحد (A=804 م²، V=3216 م³).
    """
    r = reading
    clar = r.clarifier
    area = float(clar.surface_area_m2)      # A = 804 م² (حوض واحد)
    vol = float(clar.volume_m3)             # V = 3216 م³ (حوض واحد)

    flow = float(r.flow_q)                           # تصريف الحوض الواحد Q
    mlss = float(r.mlss)
    qr = float(r.ras_percent) * flow / 100          # RAS m³/d = %RAS × Q /100
    qw = float(r.was_percent) * flow / 100          # WAS m³/d = %WAS × Q /100
    inflow = flow + qr                               # Q + Qr (مقام HRT و SLR)
    svi = (float(r.sv30) * 1000 / mlss) if mlss else 0        # SVI = SV30×1000 / MLSS
    sor = (flow / area) if area else 0                        # SOR = Q / A
    slr = ((inflow / 24 * (mlss / 1000)) / area) if area else 0   # SLR = [(Q+Qr)/24 × MLSS/1000] / A
    hrt = (vol / inflow * 24) if inflow else 0               # HRT = [V / (Q+Qr)] × 24

    # حدّ أمان أعلى (يمنع تجاوز سعة الحقول عند إدخال تصريف صغير جداً بالخطأ)
    svi = min(svi, 9_999_999)
    sor = min(sor, 9_999_999)
    slr = min(slr, 9_999_999)
    hrt = min(hrt, 9_999_999)

    def removal(cin, cout):
        cin = float(cin)
        return (cin - float(cout)) * 100 / cin if cin else 0

    metric, _ = Metric.objects.update_or_create(
        reading=r,
        defaults={
            "qr_ras": _d(round(qr, 2)),
            "qw_was": _d(round(qw, 2)),
            "svi": _d(round(svi, 2)),
            "sor": _d(round(sor, 3)),
            "slr": _d(round(slr, 3)),
            "hrt": _d(round(hrt, 3)),
            "tss_removal": _d(round(removal(r.tss_in, r.tss_out), 2)),
            "cod_removal": _d(round(removal(r.cod_in, r.cod_out), 2)),
            "bod_removal": _d(round(removal(r.bod_in, r.bod_out), 2)),
        },
    )
    return metric
