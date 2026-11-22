"""OAP state machines and lifecycle transitions.

Pure Python: no Django, no DRF, no Celery.
All transitions and guard conditions are verified here.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.oap.domain.errors import (
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
)

# Standard Actors
STUDENT = "student"
PG_STUDENT = "pg_student"
FACULTY = "faculty"
THESIS_SUPERVISOR = "thesis_supervisor"
TA_SUPERVISOR = "ta_supervisor"
HOD = "hod"
ACADEMIC_ADMIN = "academic_admin"
DEPARTMENT_ADMIN = "department_admin"
SYSTEM = "system"

# Authority Actors for No-Dues
LIBRARIAN = "librarian"
HOSTEL_WARDEN = "hostel_warden"
MESS_INCHARGE = "mess_incharge"
DEPT_VERIFIER = "dept_verifier"
LAB_SUPERVISOR = "lab_supervisor"
ACAD_VERIFIER = "acad_verifier"
STUDENT_SECTION_VERIFIER = "student_section_verifier"


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actor: str
    guard: str | None = None


# ==============================================================================
# 1. LEAVE APPLICATION STATE MACHINE (BW-OAP-01, BW-OAP-02, CW-OAP-01, OA-BR-11)
# ==============================================================================
LEAVE_DRAFT = "draft"
LEAVE_SUBMITTED = "submitted"
LEAVE_APPROVED = "approved"
LEAVE_REJECTED = "rejected"

LEAVE_TERMINAL = frozenset({LEAVE_APPROVED, LEAVE_REJECTED})

LEAVE_TRANSITIONS = (
    Transition(LEAVE_DRAFT, LEAVE_SUBMITTED, STUDENT),
    Transition(LEAVE_SUBMITTED, LEAVE_APPROVED, HOD),
    Transition(LEAVE_SUBMITTED, LEAVE_REJECTED, HOD),
)


def can_transition_leave(frm: str, to: str, actor: str) -> bool:
    for t in LEAVE_TRANSITIONS:
        if t.frm == frm and t.to == to:
            return t.actor == actor
    return False


def validate_leave_transition(frm: str, to: str, actor: str) -> None:
    legal_target = any(t.frm == frm and t.to == to for t in LEAVE_TRANSITIONS)
    if not legal_target:
        raise InvalidTransition(frm, to, entity="LeaveApplication")
    matching = [t for t in LEAVE_TRANSITIONS if t.frm == frm and t.to == to and t.actor == actor]
    if not matching:
        raise ActorNotAllowed(actor, f"transition leave from {frm} to {to}", entity="LeaveApplication")


# ==============================================================================
# 2. BONAFIDE CERTIFICATE STATE MACHINE (BW-OAP-03, BW-OAP-04, CW-OAP-02, OA-BR-21, 22)
# ==============================================================================
BONAFIDE_SUBMITTED = "submitted"
BONAFIDE_APPROVED = "approved"
BONAFIDE_REJECTED = "rejected"

BONAFIDE_TERMINAL = frozenset({BONAFIDE_APPROVED, BONAFIDE_REJECTED})

BONAFIDE_TRANSITIONS = (
    Transition(BONAFIDE_SUBMITTED, BONAFIDE_APPROVED, ACADEMIC_ADMIN),
    Transition(BONAFIDE_SUBMITTED, BONAFIDE_REJECTED, ACADEMIC_ADMIN),
)


def validate_bonafide_transition(frm: str, to: str, actor: str) -> None:
    legal = any(t.frm == frm and t.to == to for t in BONAFIDE_TRANSITIONS)
    if not legal:
        raise InvalidTransition(frm, to, entity="BonafideRequest")
    matching = [t for t in BONAFIDE_TRANSITIONS if t.frm == frm and t.to == to and t.actor == actor]
    if not matching:
        raise ActorNotAllowed(actor, f"transition bonafide from {frm} to {to}", entity="BonafideRequest")


def can_download_bonafide(status: str) -> bool:
    """OA-BR-22: A bonafide certificate shall be available for download only after the request is approved."""
    return status == BONAFIDE_APPROVED


# ==============================================================================
# 3. NO-DUES CLEARANCE STATE MACHINE (BW-OAP-05, BW-OAP-06, CW-OAP-03, OA-BR-31..34)
# ==============================================================================
NODUES_SUBMITTED = "submitted"
NODUES_IN_PROGRESS = "in_progress"
NODUES_CLEARED = "cleared"
NODUES_REJECTED = "rejected"

NODUES_TERMINAL = frozenset({NODUES_CLEARED, NODUES_REJECTED})

NODUES_DOMAIN_LIBRARY = "library"
NODUES_DOMAIN_HOSTEL = "hostel"
NODUES_DOMAIN_MESS = "mess"
NODUES_DOMAIN_DEPARTMENT = "department"
NODUES_DOMAIN_LAB = "lab"
NODUES_DOMAIN_ACADEMIC = "academic"
NODUES_DOMAIN_STUDENT_SECTION = "student_section"

MANDATORY_NODUES_DOMAINS = frozenset({
    NODUES_DOMAIN_LIBRARY,
    NODUES_DOMAIN_HOSTEL,
    NODUES_DOMAIN_MESS,
    NODUES_DOMAIN_DEPARTMENT,
    NODUES_DOMAIN_LAB,
    NODUES_DOMAIN_ACADEMIC,
    NODUES_DOMAIN_STUDENT_SECTION,
})

AUTHORITY_STATUS_PENDING = "pending"
AUTHORITY_STATUS_CLEARED = "cleared"
AUTHORITY_STATUS_DUES_PENDING = "dues_pending"

DOMAIN_AUTHORITY_ACTORS = {
    NODUES_DOMAIN_LIBRARY: LIBRARIAN,
    NODUES_DOMAIN_HOSTEL: HOSTEL_WARDEN,
    NODUES_DOMAIN_MESS: MESS_INCHARGE,
    NODUES_DOMAIN_DEPARTMENT: DEPT_VERIFIER,
    NODUES_DOMAIN_LAB: LAB_SUPERVISOR,
    NODUES_DOMAIN_ACADEMIC: ACAD_VERIFIER,
    NODUES_DOMAIN_STUDENT_SECTION: STUDENT_SECTION_VERIFIER,
}


def validate_nodues_authority_action(domain: str, actor: str) -> None:
    """OA-BR-31: Each authority may record clearance only for its own institutional domain."""
    if domain not in MANDATORY_NODUES_DOMAINS:
        raise GuardFailed("invalid_domain", f"Unknown no-dues domain: {domain}")
    expected_actor = DOMAIN_AUTHORITY_ACTORS.get(domain)
    # Actor may match the specific authority role or have appropriate admin permission
    if actor != expected_actor and actor != ACADEMIC_ADMIN:
        raise ActorNotAllowed(actor, f"verify {domain} no-dues", entity="NoDuesAuthorityRecord")


def validate_nodues_finalization(domain_statuses: dict[str, str], actor: str) -> None:
    """OA-BR-33: Finalized only after all seven mandatory authorities recorded cleared."""
    if actor != ACADEMIC_ADMIN:
        raise ActorNotAllowed(actor, "finalize no-dues", entity="NoDuesRequest")

    missing_domains = MANDATORY_NODUES_DOMAINS - set(domain_statuses.keys())
    if missing_domains:
        raise GuardFailed("missing_domains", f"Missing verifications from: {sorted(missing_domains)}")

    not_cleared = [
        d for d, status in domain_statuses.items()
        if d in MANDATORY_NODUES_DOMAINS and status != AUTHORITY_STATUS_CLEARED
    ]
    if not_cleared:
        raise GuardFailed("unresolved_dues", f"Cannot finalize no-dues: outstanding domains {sorted(not_cleared)}")


def can_download_nodues_certificate(status: str) -> bool:
    """OA-BR-34: Made downloadable only after Academic Administrator finalization."""
    return status == NODUES_CLEARED


# ==============================================================================
# 4. ASSISTANTSHIP CLAIM STATE MACHINE (BW-OAP-07, BW-OAP-08, CW-OAP-04, OA-BR-41..46, 52)
# ==============================================================================
CLAIM_SUBMITTED = "submitted"
CLAIM_THESIS_VERIFIED = "thesis_verified"
CLAIM_TA_VERIFIED = "ta_verified"
CLAIM_SUPERVISORS_VERIFIED = "supervisors_verified"
CLAIM_DEPARTMENT_FORWARDED = "department_forwarded"
CLAIM_APPROVED = "approved"
CLAIM_REJECTED = "rejected"
CLAIM_DISBURSED = "disbursed"

CLAIM_TERMINAL = frozenset({CLAIM_REJECTED, CLAIM_DISBURSED})


def resolve_claim_supervisor_state(
    current_status: str,
    verifying_role: str,
) -> str:
    """OA-BR-42: Both thesis and TA supervisor roles must verify (in either order)."""
    if verifying_role == THESIS_SUPERVISOR:
        if current_status == CLAIM_SUBMITTED:
            return CLAIM_THESIS_VERIFIED
        if current_status == CLAIM_TA_VERIFIED:
            return CLAIM_SUPERVISORS_VERIFIED
        raise InvalidTransition(current_status, CLAIM_SUPERVISORS_VERIFIED, entity="AssistantshipClaim")

    if verifying_role == TA_SUPERVISOR:
        if current_status == CLAIM_SUBMITTED:
            return CLAIM_TA_VERIFIED
        if current_status == CLAIM_THESIS_VERIFIED:
            return CLAIM_SUPERVISORS_VERIFIED
        raise InvalidTransition(current_status, CLAIM_SUPERVISORS_VERIFIED, entity="AssistantshipClaim")

    raise ActorNotAllowed(verifying_role, "record supervisor verification", entity="AssistantshipClaim")


def validate_claim_department_forward(current_status: str, actor: str) -> None:
    """OA-BR-43: Department review occurs only after both supervisor-role verifications are complete."""
    if actor != DEPARTMENT_ADMIN:
        raise ActorNotAllowed(actor, "forward assistantship claim", entity="AssistantshipClaim")
    if current_status != CLAIM_SUPERVISORS_VERIFIED:
        raise GuardFailed(
            "supervisors_not_verified",
            f"Cannot forward claim in status {current_status!r}; both supervisors must verify first."
        )


def validate_claim_hod_decision(current_status: str, actor: str, decision: str) -> None:
    """OA-BR-44: HoD is the stated authority to approve or reject after review."""
    if actor != HOD:
        raise ActorNotAllowed(actor, "decide assistantship claim", entity="AssistantshipClaim")
    if current_status != CLAIM_DEPARTMENT_FORWARDED:
        raise GuardFailed(
            "not_department_forwarded",
            f"Cannot decide claim in status {current_status!r}; must be department forwarded first."
        )
    if decision not in (CLAIM_APPROVED, CLAIM_REJECTED):
        raise InvalidTransition(current_status, decision, entity="AssistantshipClaim")


def validate_stipend_disbursement(current_status: str, actor: str) -> None:
    """OA-BR-45: Stipend processing applies only to HoD-approved assistantship claims."""
    if actor != ACADEMIC_ADMIN:
        raise ActorNotAllowed(actor, "process stipend disbursement", entity="AssistantshipClaim")
    if current_status != CLAIM_APPROVED:
        raise GuardFailed(
            "not_approved",
            f"Cannot disburse stipend for claim in status {current_status!r}; must be HoD-approved."
        )


# ==============================================================================
# 5. GRADUATE SEMINAR STATE MACHINE (BW-OAP-09, OA-BR-61..63)
# ==============================================================================
SEMINAR_REQUESTED = "requested"
SEMINAR_SCHEDULED = "scheduled"

SEMINAR_TERMINAL = frozenset({SEMINAR_SCHEDULED})


def validate_seminar_schedule(current_status: str, actor: str) -> None:
    """OA-BR-62: Dept Admin schedules seminar directly from requested status. No separate approval."""
    if actor != DEPARTMENT_ADMIN:
        raise ActorNotAllowed(actor, "schedule graduate seminar", entity="GraduateSeminar")
    if current_status != SEMINAR_REQUESTED:
        raise InvalidTransition(current_status, SEMINAR_SCHEDULED, entity="GraduateSeminar")
