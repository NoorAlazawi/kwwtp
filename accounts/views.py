from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from .forms import UserCreateForm, StyledPasswordChangeForm
from .models import User


def _can_manage(user):
    """إدارة المستخدمين متاحة للمشرف/المدير أو طاقم الإدارة (is_staff)."""
    return user.is_staff or getattr(user, "is_supervisor", False) or user.is_superuser


@login_required
def user_list(request):
    if not _can_manage(request.user):
        raise PermissionDenied("لا تملك صلاحية إدارة المستخدمين.")
    users = User.objects.select_related("plant").order_by("-is_active", "username")
    return render(request, "accounts/user_list.html", {
        "users": users, "can_manage": True,
    })


@login_required
def user_create(request):
    if not _can_manage(request.user):
        raise PermissionDenied("لا تملك صلاحية إضافة مستخدمين.")
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            u = form.save()
            messages.success(request, f"تم إنشاء المستخدم «{u.username}» بنجاح.")
            return redirect("user_list")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form})


@login_required
def password_change(request):
    """تغيير كلمة مرور المستخدم الحالي."""
    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)   # يُبقي الجلسة نشطة بعد التغيير
            messages.success(request, "تم تغيير كلمة المرور بنجاح.")
            return redirect("password_change")
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})
