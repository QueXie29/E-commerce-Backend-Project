from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_admin_user(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or getattr(user, "role", None) == "admin")
    )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin_user(request.user)


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_admin_user(request.user):
            return True
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)
