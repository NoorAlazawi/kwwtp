import json
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from monitoring.models import DailyReading, Clarifier

CIRC = 276.46


def _gauge(value, good=True):
    if value is None:
        return {"value": None, "offset": CIRC, "color": "#8598b3", "text": "#8598b3"}
    v = float(value)
    if good:
        color, text = (("#12b981", "#0b8f63") if v >= 85 else
                       ("#f5a524", "#b9760a") if v >= 70 else ("#f2545b", "#c33"))
    else:
        color, text = (("#12b981", "#0b8f63") if v <= 20 else
                       ("#f5a524", "#b9760a") if v <= 40 else ("#f2545b", "#c33"))
    offset = CIRC - CIRC * min(v, 100) / 100
    return {"value": round(v), "offset": round(offset, 1), "color": color, "text": text}


def _arc(value, vmin, vmax, zones):
    if value is None:
        return {"value": None, "angle": 90, "color": "#8598b3"}
    v = float(value)
    frac = max(0, min(1, (v - vmin) / (vmax - vmin))) if vmax > vmin else 0
    color = "#12b981"
    for lo, hi, c in zones:
        if lo <= v < hi:
            color = c
            break
    return {"value": round(v, 2), "angle": round(180 * frac, 1), "color": color}


@login_required
def dashboard(request):
    clarifiers = list(Clarifier.objects.select_related("plant").order_by("number"))
    if not clarifiers:
        return render(request, "dashboard/dashboard.html", {"latest": None, "clarifiers": []})

    # ------- الفلترة: الحوض المختار + تاريخ نهاية الفترة (7 أيام تنتهي عنده) -------
    sel_num = request.GET.get("clarifier")
    clarifier = next((c for c in clarifiers if str(c.number) == sel_num), clarifiers[0])

    qs = DailyReading.objects.filter(clarifier=clarifier)
    all_dates = list(qs.order_by("date").values_list("date", flat=True))
    if not all_dates:
        return render(request, "dashboard/dashboard.html",
                      {"latest": None, "clarifiers": clarifiers, "sel_clarifier": clarifier})

    min_date, max_date = all_dates[0], all_dates[-1]
    from datetime import date as _date
    today = _date.today()
    end_str = request.GET.get("end")
    try:
        # افتراضياً: اليوم الحالي — إلا إذا اختار المستخدم تاريخاً معيّناً
        end_date = _date.fromisoformat(end_str) if end_str else today
    except (ValueError, TypeError):
        end_date = today
    # ضمن المدى المتاح؛ إن لم تكن بيانات اليوم متوفّرة بعد يُعرض أحدث يوم متاح
    end_date = max(min_date, min(end_date, max_date))
    start_date = end_date - timedelta(days=6)

    window = list(
        qs.filter(date__gte=start_date, date__lte=end_date)
        .select_related("metric", "scores").order_by("date")
    )
    if not window:  # احتياط: آخر 7 قراءات
        window = list(qs.select_related("metric", "scores").order_by("-date")[:7])[::-1]

    latest = window[-1]
    m = getattr(latest, "metric", None)
    s = getattr(latest, "scores", None)
    swd = float(clarifier.side_water_depth) or 4.0
    diagnoses = latest.diagnoses.select_related("parameter").all()
    raw_alarms = latest.alarms.select_related("parameter").filter(acknowledged=False)

    # --- تنبيهات مع نظام التغذية الرجعية (تنبؤ بالحلول عند تكرار المؤشرات) ---
    from analytics.models import DiagnosisRule, Diagnosis as _Diag
    # حالة كل مؤشر في هذه القراءة (لربط التنبيه بالقاعدة)
    diag_status = {d.parameter_id: d.status for d in diagnoses}
    alarms = []
    for a in raw_alarms:
        st = diag_status.get(a.parameter_id, "critical" if a.level == "critical" else "warning")
        rule = DiagnosisRule.objects.filter(parameter=a.parameter, status=st).first()
        # عدد مرّات تكرار نفس (المؤشر+الحالة) عبر كل القراءات = قوة النمط
        recurrence = _Diag.objects.filter(parameter=a.parameter, status=st).count()
        alarms.append({
            "pk": a.pk, "level": a.level, "get_level_display": a.get_level_display(),
            "parameter": a.parameter, "action": a.action, "value": a.value,
            "status": st,
            "learned": bool(rule and rule.edited),          # حل مُتعلّم (عدّله المشغّل)
            "confirmed": rule.times_confirmed if rule else 0,  # مرّات التأكيد (تغذية رجعية)
            "recurrence": recurrence,                        # تكرار النمط
        })

    anim = {
        "dates": [r.date.strftime("%m/%d") for r in window],
        "flow": [float(r.flow_q) for r in window],
        "ras": [float(r.metric.qr_ras) if hasattr(r, "metric") else 0 for r in window],
        "was": [float(r.metric.qw_was) if hasattr(r, "metric") else 0 for r in window],
        "blanket": [float(r.sludge_blanket) for r in window],
        "svi": [float(r.metric.svi) if hasattr(r, "metric") else 0 for r in window],
        "mlss": [float(r.mlss) for r in window],
        "tss_out": [float(r.tss_out) for r in window],
        "cod_out": [float(r.cod_out) for r in window],
        "bod_out": [float(r.bod_out) for r in window],
        "tss_in": [float(r.tss_in) for r in window],
        "chi": [float(r.scores.chi) if hasattr(r, "scores") else 0 for r in window],
        "cri": [float(r.scores.cri) if hasattr(r, "scores") else 0 for r in window],
        "tss_rem": [float(r.metric.tss_removal) if hasattr(r, "metric") else 0 for r in window],
        "cod_rem": [float(r.metric.cod_removal) if hasattr(r, "metric") else 0 for r in window],
        "bod_rem": [float(r.metric.bod_removal) if hasattr(r, "metric") else 0 for r in window],
        "area": float(clarifier.surface_area_m2), "vol": float(clarifier.volume_m3),
        "ntanks": clarifier.plant.clarifiers_in_service or clarifier.plant.num_clarifiers or 8,
        "swd": swd,
    }

    arc_gauges = []
    if m:
        arc_gauges = [
            {"label": "SOR", "unit": "m³/m²·d", "range": "16 – 28",
             **_arc(m.sor, 0, 45, [(0,16,"#f5a524"),(16,28,"#12b981"),(28,999,"#f2545b")])},
            {"label": "SLR", "unit": "kg/m²·h", "range": "4 – 6",
             **_arc(m.slr, 0, 12, [(0,4,"#f5a524"),(4,6,"#12b981"),(6,999,"#f2545b")])},
            {"label": "HRT", "unit": "hr", "range": "2 – 4",
             **_arc(m.hrt, 0, 8, [(0,2,"#f5a524"),(2,4,"#12b981"),(4,999,"#f2545b")])},
            {"label": "RAS", "unit": "%", "range": "25 – 75",
             **_arc(latest.ras_percent, 0, 120, [(0,25,"#f5a524"),(25,75,"#12b981"),(75,999,"#f5a524")])},
            {"label": "WAS", "unit": "%", "range": "0.3 – 0.4",
             **_arc(latest.was_percent, 0, 1, [(0,0.3,"#f5a524"),(0.3,0.4,"#12b981"),(0.4,999,"#f2545b")])},
        ]

    gauges = []
    if s:
        gauges = [
            {"label": "CHI الصحة", "status": s.chi_status, **_gauge(s.chi, good=True)},
            {"label": "CSI الاستقرار", "status": s.csi_status or "—", **_gauge(s.csi, good=True)},
            {"label": "CRI المخاطر", "status": s.cri_level, **_gauge(s.cri, good=False)},
        ]

    blk = float(latest.sludge_blanket)
    blk_state = ("LOW", "#3b82f6") if blk < 1 else \
                ("NORMAL", "#12b981") if blk < 3 else \
                ("HIGH", "#f5a524") if blk < 4 else ("CRITICAL", "#f2545b")
    # نسبة عمق طبقة الحمأة من عمق الحوض (SWD)
    blk_depth_frac = round(min(blk / swd, 0.9), 3)
    # موضع وارتفاع طبقة الحمأة في المقطع (المنطقة المائية y:74..300 = 226px، القاع y=300)
    sludge_h = round(226 * blk_depth_frac)
    sludge_y = 300 - sludge_h

    # خيارات فترات جاهزة (كل أسبوع ينتهي بسبت مثلاً) — نبني قائمة تواريخ نهاية ممكنة
    period_options = []
    d = max_date
    while d >= min_date + timedelta(days=6):
        period_options.append(d)
        d -= timedelta(days=7)

    # --- نظرة عامة: حالة كل الأحواض في اليوم المختار (end_date) ---
    basins_overview = []
    for c in clarifiers:
        # قراءة اليوم المختار، أو أقرب قراءة سابقة له
        rd = (DailyReading.objects.filter(clarifier=c, date__lte=end_date)
              .select_related("metric", "scores").order_by("-date").first())
        if not rd:
            basins_overview.append({"number": c.number, "label": c.label,
                                    "color": c.ui_color, "has_data": False})
            continue
        sc = getattr(rd, "scores", None)
        mt = getattr(rd, "metric", None)
        b = float(rd.sludge_blanket)
        bstate, bcol = (("منخفض", "#4a90d9") if b < 1 else
                        ("طبيعي", "#28b487") if b < 3 else
                        ("مرتفع", "#e8a020") if b < 4 else ("حرج", "#e35d75"))
        chi = float(sc.chi) if sc else None
        cri = float(sc.cri) if sc else None
        # لون البطاقة حسب الصحة العامة (CHI)
        if chi is None:
            hcol = "#8a9bb2"
        elif chi >= 85:
            hcol = "#28b487"
        elif chi >= 70:
            hcol = "#e8a020"
        else:
            hcol = "#e35d75"
        n_alarms = rd.alarms.filter(acknowledged=False).count()
        basins_overview.append({
            "number": c.number, "label": c.label, "color": c.ui_color,
            "has_data": True, "date": rd.date,
            "chi": round(chi) if chi is not None else None, "hcol": hcol,
            "cri": round(cri) if cri is not None else None,
            "svi": round(float(mt.svi)) if mt else None,
            "blanket": round(b, 2), "bstate": bstate, "bcol": bcol,
            "alarms": n_alarms,
            "is_selected": c.number == clarifier.number,
        })

    context = {
        "latest": latest, "m": m, "s": s, "diagnoses": diagnoses, "alarms": alarms,
        "gauges": gauges, "arc_gauges": arc_gauges, "anim_json": json.dumps(anim),
        "blk_pct": round(min(blk / 6 * 100, 100), 1),
        "blk_state": blk_state[0], "blk_color": blk_state[1],
        "blk_depth_frac": blk_depth_frac, "swd": swd,
        "sludge_h": sludge_h, "sludge_y": sludge_y,
        # الفلترة
        "clarifiers": clarifiers, "sel_clarifier": clarifier,
        "sel_color": clarifier.ui_color,
        # التوصيات تخصّ اليوم المختار فقط (يوماً بيوم)
        "recommendations": clarifier.recommendations.filter(date=end_date),
        "start_date": start_date, "end_date": end_date,
        "min_date": min_date, "max_date": max_date,
        "period_options": period_options,
        "basins_overview": basins_overview,
    }
    return render(request, "dashboard/dashboard.html", context)


@login_required
def monitor_screen(request):
    """شاشة مراقبة منفصلة: الفهارس المركّبة + مقارنة الأداء فقط (عرض حائطي احترافي)."""
    from datetime import date as _date
    clarifiers = list(Clarifier.objects.select_related("plant").order_by("number"))
    if not clarifiers:
        return render(request, "dashboard/monitor.html", {"latest": None, "clarifiers": []})
    sel_num = request.GET.get("clarifier")
    clarifier = next((c for c in clarifiers if str(c.number) == sel_num), clarifiers[0])

    qs = DailyReading.objects.filter(clarifier=clarifier)
    # افتراضياً اليوم الحالي وإلا أحدث قراءة
    today = _date.today()
    latest = (qs.filter(date__lte=today).select_related("metric", "scores").order_by("-date").first()
              or qs.select_related("metric", "scores").order_by("-date").first())
    if not latest:
        return render(request, "dashboard/monitor.html",
                      {"latest": None, "clarifiers": clarifiers, "sel_clarifier": clarifier})

    m = getattr(latest, "metric", None)
    s = getattr(latest, "scores", None)
    arc_gauges = []
    if m:
        arc_gauges = [
            {"label": "SOR", "unit": "m³/m²·d", "range": "16 – 28",
             **_arc(m.sor, 0, 45, [(0,16,"#f5a524"),(16,28,"#12b981"),(28,999,"#f2545b")])},
            {"label": "SLR", "unit": "kg/m²·h", "range": "4 – 6",
             **_arc(m.slr, 0, 12, [(0,4,"#f5a524"),(4,6,"#12b981"),(6,999,"#f2545b")])},
            {"label": "HRT", "unit": "hr", "range": "2 – 4",
             **_arc(m.hrt, 0, 8, [(0,2,"#f5a524"),(2,4,"#12b981"),(4,999,"#f2545b")])},
            {"label": "RAS", "unit": "%", "range": "25 – 75",
             **_arc(latest.ras_percent, 0, 120, [(0,25,"#f5a524"),(25,75,"#12b981"),(75,999,"#f5a524")])},
            {"label": "WAS", "unit": "%", "range": "0.3 – 0.4",
             **_arc(latest.was_percent, 0, 1, [(0,0.3,"#f5a524"),(0.3,0.4,"#12b981"),(0.4,999,"#f2545b")])},
        ]
    gauges = []
    if s:
        gauges = [
            {"label": "CHI الصحة", "status": s.chi_status, **_gauge(s.chi, good=True)},
            {"label": "CSI الاستقرار", "status": s.csi_status or "—", **_gauge(s.csi, good=True)},
            {"label": "CRI المخاطر", "status": s.cri_level, **_gauge(s.cri, good=False)},
        ]
    n_alarms = latest.alarms.filter(acknowledged=False).count()
    n_crit = latest.alarms.filter(acknowledged=False, level="critical").count()
    overall = "critical" if n_crit else ("warning" if n_alarms else "ok")
    return render(request, "dashboard/monitor.html", {
        "latest": latest, "m": m, "s": s,
        "arc_gauges": arc_gauges, "gauges": gauges,
        "clarifiers": clarifiers, "sel_clarifier": clarifier,
        "sel_color": clarifier.ui_color,
        "n_alarms": n_alarms, "n_crit": n_crit, "overall": overall,
    })


from django.views.decorators.http import require_POST
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required as _login_required
from analytics.models import Recommendation, Alarm, Diagnosis, DiagnosisRule
from monitoring.models import Clarifier as _Clarifier


@_login_required
@require_POST
def alarm_edit(request, pk):
    """تعديل نص إجراء التنبيه — يُخزَّن في قاعدة التشخيص (مؤشر+حالة) فيُطبَّق على
    كل القراءات الحالية والمستقبلية التي تحمل نفس الحالة لنفس المؤشر."""
    alarm = get_object_or_404(Alarm.objects.select_related("parameter", "reading__clarifier"), pk=pk)
    new_action = (request.POST.get("action") or "").strip()
    param = alarm.parameter
    # حالة التشخيص المقابلة لهذا التنبيه
    diag = Diagnosis.objects.filter(reading=alarm.reading, parameter=param).first()
    status = diag.status if diag else ("critical" if alarm.level == "critical" else "warning")
    if new_action:
        rule, _ = DiagnosisRule.objects.get_or_create(parameter=param, status=status)
        rule.action = new_action[:1000]
        rule.edited = True                       # صار حلاً مُتعلّماً
        rule.times_confirmed = (rule.times_confirmed or 0) + 1   # تغذية رجعية: تأكيد الحل
        rule.updated_by = request.user
        rule.save()
        # نشر التعديل على كل التشخيصات والتنبيهات التي تحمل نفس (المؤشر، الحالة)
        reading_ids = list(Diagnosis.objects.filter(parameter=param, status=status)
                           .values_list("reading_id", flat=True))
        Diagnosis.objects.filter(parameter=param, status=status).update(action=new_action[:1000])
        Alarm.objects.filter(parameter=param, reading_id__in=reading_ids).update(action=new_action[:1000])
    d = alarm.reading.date.isoformat()
    return redirect(f"/?clarifier={alarm.reading.clarifier.number}&end={d}#alertsSection")


def _rec_back(num, date_str):
    """رابط العودة مع الحفاظ على الحوض واليوم المختار."""
    d = f"&end={date_str}" if date_str else ""
    return redirect(f"/?clarifier={num}{d}#recsSection")


@_login_required
@require_POST
def rec_add(request):
    """إضافة توصية جديدة لحوض — مرتبطة باليوم المختار."""
    import datetime
    num = request.POST.get("clarifier")
    text = (request.POST.get("text") or "").strip()
    date_str = request.POST.get("date") or ""
    try:
        rec_date = datetime.date.fromisoformat(date_str) if date_str else None
    except ValueError:
        rec_date = None
    clar = _Clarifier.objects.filter(number=num).first()
    if clar and text:
        Recommendation.objects.create(clarifier=clar, date=rec_date,
                                      text=text[:300], created_by=request.user)
    return _rec_back(num, date_str)


@_login_required
@require_POST
def rec_toggle(request, pk):
    """تبديل حالة تنفيذ التوصية."""
    rec = get_object_or_404(Recommendation, pk=pk)
    rec.done = not rec.done
    rec.save(update_fields=["done", "updated_at"])
    return _rec_back(rec.clarifier.number, rec.date.isoformat() if rec.date else "")


@_login_required
@require_POST
def rec_edit(request, pk):
    """تعديل نص التوصية."""
    rec = get_object_or_404(Recommendation, pk=pk)
    text = (request.POST.get("text") or "").strip()
    if text:
        rec.text = text[:300]
        rec.save(update_fields=["text", "updated_at"])
    return _rec_back(rec.clarifier.number, rec.date.isoformat() if rec.date else "")


@_login_required
@require_POST
def rec_delete(request, pk):
    """حذف توصية."""
    rec = get_object_or_404(Recommendation, pk=pk)
    num = rec.clarifier.number
    date_str = rec.date.isoformat() if rec.date else ""
    rec.delete()
    return _rec_back(num, date_str)
