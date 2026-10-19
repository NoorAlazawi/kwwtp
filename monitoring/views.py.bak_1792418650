import json
from decimal import Decimal, InvalidOperation
from datetime import date as _date, datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from .forms import DailyReadingForm, BulkReadingForm
from .models import DailyReading, Clarifier


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


# ملخّص الإنذارات للإشعار المنبثق
def alarm_summary(readings):
    """يُلخّص إنذارات مجموعة قراءات: أعلى مستوى + عدد الحرجة/التحذيرية + أهم الرسائل."""
    crit = warn = 0
    msgs = []
    focus_clarifier = None   # رقم حوض أول حالة حرجة (للانتقال المباشر)
    focus_date = None
    for r in readings:
        for a in r.alarms.filter(is_predicted=False).select_related("parameter"):
            if a.level == "critical":
                crit += 1
                if focus_clarifier is None:
                    focus_clarifier = r.clarifier.number
                    focus_date = r.date.isoformat()
            else:
                warn += 1
            msgs.append({"level": a.level, "param": a.parameter.name_ar,
                         "basin": r.clarifier.label, "action": a.action})
    level = "critical" if crit else ("warning" if warn else "ok")
    # عند التحذير فقط: ركّز على أول حوض به تحذير
    if focus_clarifier is None and readings:
        for r in readings:
            if r.alarms.filter(is_predicted=False).exists():
                focus_clarifier = r.clarifier.number
                focus_date = r.date.isoformat()
                break
    # ترتيب: الحرجة أولاً، وبلا تكرار للنص
    msgs.sort(key=lambda x: 0 if x["level"] == "critical" else 1)
    seen, uniq = set(), []
    for mmsg in msgs:
        key = (mmsg["param"], mmsg["level"])
        if key in seen:
            continue
        seen.add(key); uniq.append(mmsg)
    return {"level": level, "crit": crit, "warn": warn, "items": uniq[:6],
            "focus_clarifier": focus_clarifier, "focus_date": focus_date}


# نموذج القراءة المنبثق: إدخال جماعي (جديد) أو تعديل فردي
@login_required
def reading_form(request):
    """يُرجع جسم النافذة المنبثقة. بلا pk = إدخال جماعي لكل الأحواض · مع pk = تعديل قراءة واحدة."""
    pk = request.GET.get("pk")
    if pk:
        instance = get_object_or_404(DailyReading, pk=pk)
        form = DailyReadingForm(instance=instance)
        html = render_to_string("monitoring/_reading_fields.html", {"form": form}, request=request)
        return JsonResponse({
            "html": html, "mode": "edit",
            "action": reverse("reading_edit", args=[instance.pk]),
            "title": f"تعديل قراءة — {instance.clarifier.label} · {instance.date}",
        })
    # إدخال جماعي — الأحواض العاملة فقط (المتوقّفة مستثناة)
    form = BulkReadingForm()
    clarifiers = Clarifier.objects.filter(is_active=True).select_related("plant").order_by("number")
    html = render_to_string("monitoring/_reading_bulk.html",
                            {"form": form, "clarifiers": clarifiers}, request=request)
    return JsonResponse({
        "html": html, "mode": "bulk",
        "action": reverse("reading_bulk_create"),
        "title": "إدخال قراءة يومية جديدة — كل الأحواض",
    })


@login_required
def reading_bulk_create(request):
    """يحفظ قراءة واحدة لكل حوض بقيم مشتركة، وطبقة حمأة خاصة بكل حوض.
    التصريف المُدخَل كلّي ويُقسَّم على عدد الأحواض العاملة.
    """
    # الأحواض العاملة فقط — الحوض المتوقّف مستثنى من الإدخال وتوزيع التصريف والحسابات
    clarifiers = list(Clarifier.objects.filter(is_active=True).select_related("plant").order_by("number"))
    plant = clarifiers[0].plant if clarifiers else None
    n_tanks = len(clarifiers) or 1   # التصريف الكلّي يُقسَّم على عدد الأحواض العاملة فقط

    if request.method != "POST":
        form = BulkReadingForm()
        return render(request, "monitoring/reading_form.html", {"form": form})

    form = BulkReadingForm(request.POST)
    # قراءة طبقة الحمأة لكل حوض
    blankets, blank_errors = {}, {}
    for c in clarifiers:
        raw = (request.POST.get(f"blanket_{c.number}") or "").strip()
        if raw == "":
            continue
        try:
            blankets[c.number] = Decimal(str(round(float(raw), 3)))
        except (ValueError, InvalidOperation):
            blank_errors[c.number] = "قيمة غير صالحة"

    if form.is_valid() and blankets and not blank_errors:
        common = form.cleaned_data
        total_flow = float(common["flow_q"])
        per_tank_flow = Decimal(str(round(total_flow / (n_tanks or 8), 3)))   # التصريف ÷ عدد الأحواض
        saved = []
        for c in clarifiers:
            if c.number not in blankets:
                continue
            defaults = {k: v for k, v in common.items() if k != "flow_q"}
            defaults["flow_q"] = per_tank_flow
            defaults["sludge_blanket"] = blankets[c.number]
            defaults["entered_by"] = request.user
            obj, _ = DailyReading.objects.update_or_create(
                clarifier=c, date=common["date"], defaults=defaults)
            saved.append(obj)
        # إعادة جلب مع الإنذارات المحسوبة
        ids = [o.id for o in saved]
        saved = list(DailyReading.objects.filter(id__in=ids)
                     .select_related("clarifier").prefetch_related("alarms__parameter"))
        summary = alarm_summary(saved)
        summary["saved"] = len(saved)
        summary["date"] = common["date"].isoformat()
        summary["per_tank_flow"] = float(per_tank_flow)
        if _is_ajax(request):
            return JsonResponse({"ok": True, "summary": summary})
        messages.success(request, f"تم حفظ {len(saved)} قراءة (حوض واحد لكل).")
        return redirect("dashboard")

    # أخطاء
    if _is_ajax(request):
        html = render_to_string("monitoring/_reading_bulk.html",
                                {"form": form, "clarifiers": clarifiers,
                                 "blank_errors": blank_errors,
                                 "no_blanket": not blankets and not blank_errors},
                                request=request)
        return JsonResponse({"ok": False, "html": html}, status=400)
    return render(request, "monitoring/reading_form.html", {"form": DailyReadingForm()})


@login_required
def reading_edit(request, pk):
    instance = get_object_or_404(DailyReading, pk=pk)
    if request.method == "POST":
        form = DailyReadingForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()   # post_save يعيد حساب المؤشرات
            if _is_ajax(request):
                r = DailyReading.objects.prefetch_related("alarms__parameter").get(pk=instance.pk)
                return JsonResponse({"ok": True, "summary": alarm_summary([r])})
            messages.success(request, "تم تحديث القراءة بنجاح.")
            return redirect("reading_list")
        if _is_ajax(request):
            html = render_to_string("monitoring/_reading_fields.html", {"form": form}, request=request)
            return JsonResponse({"ok": False, "html": html}, status=400)
    else:
        form = DailyReadingForm(instance=instance)
    return render(request, "monitoring/reading_form.html", {"form": form, "editing": True})


# استيراد قراءة فردية (احتياطي/غير منبثق)
@login_required
def reading_create(request):
    if request.method == "POST":
        form = DailyReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.entered_by = request.user
            reading.save()
            if _is_ajax(request):
                r = DailyReading.objects.prefetch_related("alarms__parameter").get(pk=reading.pk)
                return JsonResponse({"ok": True, "summary": alarm_summary([r])})
            messages.success(request, "تم حفظ القراءة ومعالجتها بنجاح.")
            return redirect("dashboard")
        if _is_ajax(request):
            html = render_to_string("monitoring/_reading_fields.html", {"form": form}, request=request)
            return JsonResponse({"ok": False, "html": html}, status=400)
    else:
        form = DailyReadingForm()
    return render(request, "monitoring/reading_form.html", {"form": form})


@login_required
def reading_list(request):
    clarifiers = Clarifier.objects.select_related("plant").all()
    sel = request.GET.get("clarifier")
    qs = DailyReading.objects.select_related("clarifier", "scores", "metric")
    if sel and sel.isdigit():
        qs = qs.filter(clarifier__number=int(sel))
        sel = int(sel)
    else:
        sel = None
    qs = qs.order_by("-date")
    total = qs.count()

    # ترقيم الصفحات
    paginator = Paginator(qs, 25)   # 25 قراءة لكل صفحة
    page_obj = paginator.get_page(request.GET.get("page"))
    readings = list(page_obj.object_list)

    # مخطّط الصفحة الحالية (بترتيب زمني تصاعدي)
    chart_src = sorted(readings, key=lambda r: r.date)
    chart = {
        "labels": [r.date.strftime("%m-%d") for r in chart_src],
        "mlss":    [float(r.mlss) for r in chart_src],
        "blanket": [float(r.sludge_blanket) for r in chart_src],
        "svi":     [float(r.metric.svi) if getattr(r, "metric", None) else None for r in chart_src],
        "flow":    [float(r.flow_q) for r in chart_src],
    }
    # سلسلة استعلام للحفاظ على فلتر الحوض عند تغيير الصفحة
    base_qs = f"clarifier={sel}&" if sel else ""
    return render(request, "monitoring/reading_list.html", {
        "readings": readings, "clarifiers": clarifiers, "sel": sel,
        "chart": chart, "count": total,
        "page_obj": page_obj, "base_qs": base_qs,
    })
