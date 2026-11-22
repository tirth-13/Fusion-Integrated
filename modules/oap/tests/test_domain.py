"""Pure Python domain tests for OAP (fast, no database)."""
import datetime
import pytest

from modules.oap.domain import rules, state_machine as sm
from modules.oap.domain.errors import (
    ActorNotAllowed,
    GuardFailed,
    IneligibleStudent,
    InvalidTransition,
    OAPDomainError,
)


# ==============================================================================
# LEAVE DOMAIN TESTS
# ==============================================================================

def test_leave_transition_success():
    assert sm.can_transition_leave(sm.LEAVE_DRAFT, sm.LEAVE_SUBMITTED, sm.STUDENT) is True
    assert sm.can_transition_leave(sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.HOD) is True
    assert sm.can_transition_leave(sm.LEAVE_SUBMITTED, sm.LEAVE_REJECTED, sm.HOD) is True


def test_leave_unauthorized_actor_fails():
    with pytest.raises(ActorNotAllowed):
        sm.validate_leave_transition(sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.STUDENT)


def test_leave_invalid_transition_fails():
    with pytest.raises(InvalidTransition):
        sm.validate_leave_transition(sm.LEAVE_APPROVED, sm.LEAVE_SUBMITTED, sm.HOD)


def test_leave_date_validation():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    yesterday = today - datetime.timedelta(days=1)

    # Valid
    rules.validate_leave_dates(today, tomorrow)

    # End before start raises error
    with pytest.raises(OAPDomainError):
        rules.validate_leave_dates(today, yesterday)


# ==============================================================================
# BONAFIDE DOMAIN TESTS
# ==============================================================================

def test_bonafide_transition_success():
    sm.validate_bonafide_transition(sm.BONAFIDE_SUBMITTED, sm.BONAFIDE_APPROVED, sm.ACADEMIC_ADMIN)
    sm.validate_bonafide_transition(sm.BONAFIDE_SUBMITTED, sm.BONAFIDE_REJECTED, sm.ACADEMIC_ADMIN)


def test_bonafide_unauthorized_actor_fails():
    with pytest.raises(ActorNotAllowed):
        sm.validate_bonafide_transition(sm.BONAFIDE_SUBMITTED, sm.BONAFIDE_APPROVED, sm.STUDENT)


def test_bonafide_download_restriction():
    assert sm.can_download_bonafide(sm.BONAFIDE_APPROVED) is True
    assert sm.can_download_bonafide(sm.BONAFIDE_SUBMITTED) is False
    assert sm.can_download_bonafide(sm.BONAFIDE_REJECTED) is False


# ==============================================================================
# NO-DUES DOMAIN TESTS (OA-BR-31..34)
# ==============================================================================

def test_nodues_seven_mandatory_domains():
    assert len(sm.MANDATORY_NODUES_DOMAINS) == 7
    expected = {"library", "hostel", "mess", "department", "lab", "academic", "student_section"}
    assert sm.MANDATORY_NODUES_DOMAINS == expected


def test_nodues_authority_domain_action():
    # Correct authority matches
    sm.validate_nodues_authority_action("library", sm.LIBRARIAN)
    sm.validate_nodues_authority_action("hostel", sm.HOSTEL_WARDEN)
    sm.validate_nodues_authority_action("mess", sm.MESS_INCHARGE)

    # Cross-domain verification prohibited (OA-BR-31)
    with pytest.raises(ActorNotAllowed):
        sm.validate_nodues_authority_action("library", sm.MESS_INCHARGE)


def test_nodues_finalization_requires_all_seven_cleared():
    # Incomplete set raises GuardFailed
    incomplete = {
        "library": sm.AUTHORITY_STATUS_CLEARED,
        "hostel": sm.AUTHORITY_STATUS_CLEARED,
    }
    with pytest.raises(GuardFailed):
        sm.validate_nodues_finalization(incomplete, sm.ACADEMIC_ADMIN)

    # One domain with dues_pending raises GuardFailed
    with_dues = {d: sm.AUTHORITY_STATUS_CLEARED for d in sm.MANDATORY_NODUES_DOMAINS}
    with_dues["library"] = sm.AUTHORITY_STATUS_DUES_PENDING
    with pytest.raises(GuardFailed):
        sm.validate_nodues_finalization(with_dues, sm.ACADEMIC_ADMIN)

    # All 7 cleared succeeds
    all_clear = {d: sm.AUTHORITY_STATUS_CLEARED for d in sm.MANDATORY_NODUES_DOMAINS}
    sm.validate_nodues_finalization(all_clear, sm.ACADEMIC_ADMIN)


def test_nodues_certificate_download():
    assert sm.can_download_nodues_certificate(sm.NODUES_CLEARED) is True
    assert sm.can_download_nodues_certificate(sm.NODUES_IN_PROGRESS) is False
    assert sm.can_download_nodues_certificate(sm.NODUES_SUBMITTED) is False


# ==============================================================================
# ASSISTANTSHIP DOMAIN TESTS (OA-BR-41..46)
# ==============================================================================

def test_pg_eligibility():
    rules.validate_pg_student_eligibility("M.Tech")
    rules.validate_pg_student_eligibility("Ph.D")
    rules.validate_pg_student_eligibility("PhD")
    rules.validate_pg_student_eligibility("M.Des")

    with pytest.raises(IneligibleStudent):
        rules.validate_pg_student_eligibility("B.Tech")


def test_dual_supervisor_verification_order():
    # Order 1: Thesis then TA
    s1 = sm.resolve_claim_supervisor_state(sm.CLAIM_SUBMITTED, sm.THESIS_SUPERVISOR)
    assert s1 == sm.CLAIM_THESIS_VERIFIED
    s2 = sm.resolve_claim_supervisor_state(s1, sm.TA_SUPERVISOR)
    assert s2 == sm.CLAIM_SUPERVISORS_VERIFIED

    # Order 2: TA then Thesis
    t1 = sm.resolve_claim_supervisor_state(sm.CLAIM_SUBMITTED, sm.TA_SUPERVISOR)
    assert t1 == sm.CLAIM_TA_VERIFIED
    t2 = sm.resolve_claim_supervisor_state(t1, sm.THESIS_SUPERVISOR)
    assert t2 == sm.CLAIM_SUPERVISORS_VERIFIED


def test_assistantship_department_forward_guard():
    # Cannot forward before both supervisors verified
    with pytest.raises(GuardFailed):
        sm.validate_claim_department_forward(sm.CLAIM_THESIS_VERIFIED, sm.DEPARTMENT_ADMIN)

    # Succeeds when both verified
    sm.validate_claim_department_forward(sm.CLAIM_SUPERVISORS_VERIFIED, sm.DEPARTMENT_ADMIN)


def test_assistantship_hod_decision():
    sm.validate_claim_hod_decision(sm.CLAIM_DEPARTMENT_FORWARDED, sm.HOD, sm.CLAIM_APPROVED)
    sm.validate_claim_hod_decision(sm.CLAIM_DEPARTMENT_FORWARDED, sm.HOD, sm.CLAIM_REJECTED)

    with pytest.raises(GuardFailed):
        sm.validate_claim_hod_decision(sm.CLAIM_SUPERVISORS_VERIFIED, sm.HOD, sm.CLAIM_APPROVED)


def test_assistantship_stipend_disbursement():
    sm.validate_stipend_disbursement(sm.CLAIM_APPROVED, sm.ACADEMIC_ADMIN)

    with pytest.raises(GuardFailed):
        sm.validate_stipend_disbursement(sm.CLAIM_DEPARTMENT_FORWARDED, sm.ACADEMIC_ADMIN)


# ==============================================================================
# GRADUATE SEMINAR DOMAIN TESTS (OA-BR-61..63)
# ==============================================================================

def test_seminar_schedule_transition():
    sm.validate_seminar_schedule(sm.SEMINAR_REQUESTED, sm.DEPARTMENT_ADMIN)

    with pytest.raises(ActorNotAllowed):
        sm.validate_seminar_schedule(sm.SEMINAR_REQUESTED, sm.STUDENT)
