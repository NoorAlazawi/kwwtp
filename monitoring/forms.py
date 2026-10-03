from django import forms
from .models import DailyReading


class BulkReadingForm(forms.ModelForm):
    """نموذج القيم المشتركة لكل الأحواض (تُدخَل مرة واحدة).
    لا يتضمّن الحوض ولا طبقة الحمأة — فهذه تُدخَل لكل حوض على حدة.
    التصريف المُدخَل هو التصريف الكلّي للمحطة ويُقسَّم على عدد الأحواض عند الحفظ.
    """
    class Meta:
        model = DailyReading
        fields = [
            "date", "flow_q", "ras_percent", "was_percent",
            "mlss", "sv30", "do", "temperature",
            "tss_in", "tss_out", "cod_in", "cod_out", "bod_in", "bod_out", "ph",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hints = {
            "flow_q": "التصريف الكلّي للمحطة (م³/يوم) — يُقسَّم على ٨ تلقائياً",
            "ras_percent": "نسبة % فقط (25–100) — ليست Qr",
            "was_percent": "نسبة % فقط (0.3–5) — ليست Qw",
            "mlss": "MLSS (mg/L)", "sv30": "SV30 (mL/L)",
        }
        self.fields["flow_q"].label = "التصريف الكلّي Q (م³/يوم)"
        for name, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " ginput").strip()
            if name in hints:
                f.widget.attrs["placeholder"] = hints[name]


class DailyReadingForm(forms.ModelForm):
    class Meta:
        model = DailyReading
        fields = [
            "clarifier", "date", "flow_q", "ras_percent", "was_percent",
            "mlss", "sv30", "do", "temperature", "sludge_blanket",
            "tss_in", "tss_out", "cod_in", "cod_out", "bod_in", "bod_out", "ph",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تلميحات إرشادية للحقول المُلتبسة (لمنع إدخال الأعمدة المحسوبة بالخطأ)
        hints = {
            "flow_q": "تصريف الحوض الواحد (م³/يوم)",
            "ras_percent": "نسبة % فقط (25–100) — ليست Qr",
            "was_percent": "نسبة % فقط (0.3–5) — ليست Qw",
            "mlss": "MLSS (mg/L)",
            "sv30": "SV30 (mL/L)",
            "sludge_blanket": "طبقة الحمأة (م)",
        }
        # إضافة صنف ginput (التأثير المحفور) لكل الحقول + التلميحات
        for name, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " ginput").strip()
            if name in hints:
                f.widget.attrs["placeholder"] = hints[name]


