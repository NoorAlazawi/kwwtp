from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User


GINPUT = "ginput"


class UserCreateForm(UserCreationForm):
    """نموذج إضافة مستخدم جديد — اسم المستخدم + الاسم + الدور + كلمة المرور."""
    class Meta:
        model = User
        fields = ["username", "first_name", "email", "role", "phone"]
        labels = {
            "username": "اسم المستخدم",
            "first_name": "الاسم الكامل",
            "email": "البريد الإلكتروني",
            "role": "الدور",
            "phone": "الهاتف",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        self.fields["first_name"].required = False
        # ترجمة تسميات حقول كلمة المرور + تلميحات
        self.fields["password1"].label = "كلمة المرور"
        self.fields["password2"].label = "تأكيد كلمة المرور"
        self.fields["password1"].help_text = (
            "٨ أحرف على الأقل · لا تكون شائعة أو رقمية بالكامل أو مشابهة لبيانات المستخدم.")
        self.fields["password2"].help_text = "أعد إدخال كلمة المرور نفسها للتأكيد."
        self.fields["username"].help_text = "حروف وأرقام والرموز @ . + - _ فقط."
        for f in self.fields.values():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " " + GINPUT).strip()


class StyledPasswordChangeForm(PasswordChangeForm):
    """تغيير كلمة مرور المستخدم الحالي — بنفس تصميم الحقول."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "كلمة المرور الحالية"
        self.fields["new_password1"].label = "كلمة المرور الجديدة"
        self.fields["new_password2"].label = "تأكيد كلمة المرور الجديدة"
        self.fields["new_password1"].help_text = (
            "٨ أحرف على الأقل · لا تكون شائعة أو رقمية بالكامل أو مشابهة لبياناتك.")
        self.fields["new_password2"].help_text = "أعد إدخال كلمة المرور الجديدة نفسها."
        for f in self.fields.values():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " " + GINPUT).strip()
