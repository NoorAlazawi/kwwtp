from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "role", "plant", "is_active")
    list_filter = ("role", "plant", "is_active")
    fieldsets = UserAdmin.fieldsets + (("معلومات إضافية", {"fields": ("role", "plant", "phone")}),)
