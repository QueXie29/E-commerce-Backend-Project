from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("id", "username", "email", "phone", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "phone")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("业务信息", {"fields": ("phone", "role")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("业务信息", {"fields": ("email", "phone", "role")}),
    )

# Register your models here.
