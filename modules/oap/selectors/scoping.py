"""Role scoping and access boundaries for OAP.

Enforces OA-BR-01 and PS 3.8:
Users can only retrieve data appropriate to their assigned roles.
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    GraduateSeminarRequest,
    LeaveApplication,
    NoDuesAuthorityRecord,
    NoDuesRequest,
    SupervisorAssignment,
    TAAssignment,
)

# Permission Constants
P_LEAVE_VIEW = "oap.leave.view"
P_LEAVE_DECIDE = "oap.leave.decide"
P_BONAFIDE_VIEW = "oap.bonafide.view"
P_BONAFIDE_DECIDE = "oap.bonafide.decide"
P_NODUES_VIEW = "oap.nodues.view"
P_NODUES_VERIFY = "oap.nodues.verify"
P_NODUES_FINALIZE = "oap.nodues.finalize"
P_ASSISTANTSHIP_VIEW = "oap.assistantship.view"
P_ASSISTANTSHIP_VERIFY = "oap.assistantship.verify"
P_ASSISTANTSHIP_FORWARD = "oap.assistantship.forward"
P_ASSISTANTSHIP_DECIDE = "oap.assistantship.decide"
P_STIPEND_PROCESS = "oap.stipend.process"
P_ASSIGNMENT_MANAGE = "oap.assignment.manage"
P_SEMINAR_MANAGE = "oap.seminar.manage"
P_SEMINAR_VIEW = "oap.seminar.view"


def _user_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has_perm(actor, perm: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_permission", None)
    if callable(checker):
        return checker(perm)
    perms = getattr(actor, "permissions", ())
    return perm in perms


def _has_any(actor, *perms: str) -> bool:
    return any(_has_perm(actor, p) for p in perms)


# ==============================================================================
# SCOPED SELECTORS
# ==============================================================================

def scoped_leaves(actor) -> QuerySet[LeaveApplication]:
    """Returns leaves visible to the actor."""
    uid = _user_id(actor)
    if uid is None:
        return LeaveApplication.objects.none()

    qs = LeaveApplication.objects.all()
    # HoD / Admin can view all or department leaves
    if _has_any(actor, P_LEAVE_DECIDE, P_LEAVE_VIEW):
        return qs
    # Students view only their own leaves
    return qs.filter(user_id=uid)


def scoped_bonafides(actor) -> QuerySet[BonafideRequest]:
    """Returns bonafide requests visible to the actor."""
    uid = _user_id(actor)
    if uid is None:
        return BonafideRequest.objects.none()

    qs = BonafideRequest.objects.all()
    if _has_any(actor, P_BONAFIDE_DECIDE, P_BONAFIDE_VIEW):
        return qs
    return qs.filter(user_id=uid)


def scoped_no_dues(actor) -> QuerySet[NoDuesRequest]:
    """Returns no-dues requests visible to the actor."""
    uid = _user_id(actor)
    if uid is None:
        return NoDuesRequest.objects.none()

    qs = NoDuesRequest.objects.all()
    if _has_any(actor, P_NODUES_FINALIZE, P_NODUES_VIEW, P_NODUES_VERIFY):
        return qs
    return qs.filter(user_id=uid)


def scoped_no_dues_authority_records(actor, domain: str | None = None) -> QuerySet[NoDuesAuthorityRecord]:
    """Returns domain verification records visible to authority or student."""
    uid = _user_id(actor)
    if uid is None:
        return NoDuesAuthorityRecord.objects.none()

    qs = NoDuesAuthorityRecord.objects.select_related("request")
    if domain:
        qs = qs.filter(authority_domain=domain)

    if _has_any(actor, P_NODUES_FINALIZE, P_NODUES_VIEW, P_NODUES_VERIFY):
        return qs
    # Student sees only their own request's records
    return qs.filter(request__user_id=uid)


def scoped_claims(actor) -> QuerySet[AssistantshipClaim]:
    """Returns assistantship claims visible to the actor."""
    uid = _user_id(actor)
    if uid is None:
        return AssistantshipClaim.objects.none()

    qs = AssistantshipClaim.objects.all()
    # Acad Admin, HoD, Dept Admin can see departmental or all claims
    if _has_any(actor, P_STIPEND_PROCESS, P_ASSISTANTSHIP_DECIDE, P_ASSISTANTSHIP_FORWARD, P_ASSISTANTSHIP_VIEW):
        return qs

    # Thesis / TA Supervisor sees claims assigned to them
    if _has_perm(actor, P_ASSISTANTSHIP_VERIFY):
        return qs.filter(
            Q(thesis_supervisor_user_id=uid) | Q(ta_supervisor_user_id=uid) | Q(user_id=uid)
        )

    # Student sees only their own
    return qs.filter(user_id=uid)


def scoped_seminars(actor) -> QuerySet[GraduateSeminarRequest]:
    """Returns seminar requests and schedules visible to the actor."""
    uid = _user_id(actor)
    if uid is None:
        return GraduateSeminarRequest.objects.none()

    qs = GraduateSeminarRequest.objects.all()
    # Dept Admin sees all requests to schedule them
    if _has_perm(actor, P_SEMINAR_MANAGE):
        return qs

    # OA-BR-63: PG students and faculty can view all SCHEDULED seminars, plus student can see their own requests
    if _has_perm(actor, P_SEMINAR_VIEW):
        return qs.filter(Q(status="scheduled") | Q(user_id=uid))

    return qs.filter(user_id=uid)


def scoped_supervisor_assignments(actor) -> QuerySet[SupervisorAssignment]:
    """Returns supervisor assignments."""
    uid = _user_id(actor)
    if uid is None:
        return SupervisorAssignment.objects.none()

    qs = SupervisorAssignment.objects.filter(is_active=True)
    if _has_any(actor, P_ASSIGNMENT_MANAGE, P_ASSISTANTSHIP_DECIDE, P_ASSISTANTSHIP_FORWARD, P_STIPEND_PROCESS):
        return qs
    return qs.filter(Q(student_user_id=uid) | Q(thesis_supervisor_user_id=uid))


def scoped_ta_assignments(actor) -> QuerySet[TAAssignment]:
    """Returns TA assignments."""
    uid = _user_id(actor)
    if uid is None:
        return TAAssignment.objects.none()

    qs = TAAssignment.objects.filter(is_active=True)
    if _has_any(actor, P_ASSIGNMENT_MANAGE, P_ASSISTANTSHIP_DECIDE, P_ASSISTANTSHIP_FORWARD, P_STIPEND_PROCESS):
        return qs
    return qs.filter(Q(student_user_id=uid) | Q(ta_supervisor_user_id=uid))
