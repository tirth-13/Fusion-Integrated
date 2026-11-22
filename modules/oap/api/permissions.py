"""Permission classes for OAP API endpoints."""
from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("oap")


class HasAnyOAPPermission(BasePermission):
    """Requires at least one of the specified permissions."""

    codes: tuple[str, ...] = ()
    message = "You do not have permission to perform this action in OAP."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        return principal.has_any_permission(*self.codes)


def RequirePermissions(*codes: str):  # noqa: N802
    return type(
        "RequirePermission_" + "_".join(codes).replace(".", "_"),
        (HasAnyOAPPermission,),
        {"codes": codes},
    )
