from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.urls import reverse_lazy

from .models import LoginToken, User

admin.site.site_url = reverse_lazy("sso_login")


@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "created_at", "expires_at", "consumed_at")
    list_filter = ("purpose", "consumed_at")
    search_fields = ("user__email",)
    readonly_fields = (
        "user",
        "token_hash",
        "purpose",
        "redirect_to",
        "expires_at",
        "consumed_at",
        "created_ip",
        "created_at",
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("display_name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )
