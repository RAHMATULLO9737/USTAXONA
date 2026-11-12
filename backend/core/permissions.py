from rest_framework.permissions import BasePermission, SAFE_METHODS

class RolePermission(BasePermission):
    allowed_roles = ()
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or request.user.role in self.allowed_roles))

class IsManagerOrAdmin(RolePermission):
    allowed_roles = ("admin", "manager")

class IsStaff(RolePermission):
    allowed_roles = ("admin", "manager", "mechanic")

class IsAdmin(RolePermission):
    allowed_roles = ("admin",)
