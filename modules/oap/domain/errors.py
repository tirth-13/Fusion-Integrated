"""Pure Python domain errors for OAP.

No framework dependencies.
"""
from __future__ import annotations


class OAPDomainError(Exception):
    """Base domain error for OAP."""

    def __init__(self, message: str = ""):
        super().__init__(message or "OAP domain rule violation.")
        self.message = message


class InvalidTransition(OAPDomainError):
    def __init__(self, frm: str, to: str, entity: str = "entity"):
        super().__init__(f"Cannot move {entity} from {frm!r} to {to!r}.")
        self.frm = frm
        self.to = to
        self.entity = entity


class ActorNotAllowed(OAPDomainError):
    def __init__(self, actor_kind: str, action: str, entity: str = "entity"):
        super().__init__(f"A {actor_kind} is not allowed to {action} this {entity}.")
        self.actor_kind = actor_kind
        self.action = action
        self.entity = entity


class GuardFailed(OAPDomainError):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


class IneligibleStudent(OAPDomainError):
    def __init__(self, reason: str = ""):
        super().__init__(reason or "Student is not eligible for this procedure.")
        self.reason = reason
