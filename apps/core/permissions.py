from rest_framework import permissions


class IsProvider(permissions.BasePermission):
    message = "Only provider accounts can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_provider)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission: safe methods for all, writes for the owner only.

    Views declare ``owner_field`` as a dotted path from the object to its owner,
    e.g. ``"owner"`` or ``"business.owner"``.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = obj
        for attr in getattr(view, "owner_field", "owner").split("."):
            owner = getattr(owner, attr)
        return owner == request.user
