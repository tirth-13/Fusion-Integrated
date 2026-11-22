"""Spec-based tests for Business Rules (OA-BR-01..63).

Generated from docs/09-oap/spec-tests/BR_DESIGN.json per Assignment 9 Prompt B.
Rules:
- test_id and source_id in docstring.
- Tests pure domain rules and service enforcement.
- Pass without skipping.
"""
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
from modules.oap.services import (
    assistantships as assistantship_service,
    bonafide as bonafide_service,
    leaves as leave_service,
    no_dues as nodues_service,
    seminars as seminar_service,
)

pytestmark = pytest.mark.django_db


# --- OA-BR-01: Role-Based Access and Data Scope ---
def test_br_tc_001():
    """BR-TC-001 | OA-BR-01 permitted: Authorized role can use a permitted function."""
    app = leave_service.submit_leave(
        user_id=101,
        student_name="Alice",
        programme="UG",
        department="CSE",
        leave_type="casual",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 3),
        reason="Family event",
    )
    assert app.id is not None
    assert app.status == "submitted"


def test_br_tc_002():
    """BR-TC-002 | OA-BR-01 prohibited-function: Student cannot execute HoD-only approval."""
    with pytest.raises(ActorNotAllowed):
        sm.validate_leave_transition(sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.STUDENT)


def test_br_tc_003():
    """BR-TC-003 | OA-BR-01 prohibited-record: Cross-record scoping denial."""
    # Verified by scoping selector
    from modules.oap.selectors import scoping

    class MockPrincipal:
        user_id = 101
        permissions = frozenset(["oap.leave.view_self"])
        def has_permission(self, p): return p in self.permissions

    LeaveApplication.objects.create(
        user_id=102, student_name="Bob", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical", status="submitted"
    )
    qs = scoping.scoped_leaves(MockPrincipal())
    assert not qs.filter(user_id=102).exists()


# --- OA-BR-11: Leave Decision Authority ---
def test_br_tc_011():
    """BR-TC-011 | OA-BR-11 hod-approved: HoD approves student leave."""
    app = LeaveApplication.objects.create(
        user_id=101, student_name="Alice", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Family event", status="submitted"
    )
    res = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="approve", remarks="OK")
    assert res.status == "approved"
    assert res.hod_user_id == 901


def test_br_tc_012():
    """BR-TC-012 | OA-BR-11 hod-rejected: HoD rejects student leave."""
    app = LeaveApplication.objects.create(
        user_id=101, student_name="Alice", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Family event", status="submitted"
    )
    res = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="reject", remarks="Denied")
    assert res.status == "rejected"


def test_br_tc_013():
    """BR-TC-013 | OA-BR-11 non-hod-refusal: Non-HoD cannot decide leave."""
    with pytest.raises(ActorNotAllowed):
        sm.validate_leave_transition(sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.FACULTY)


# --- OA-BR-21 & OA-BR-22: Bonafide Authority & Download Restriction ---
def test_br_tc_021():
    """BR-TC-021 | OA-BR-21 acad-admin-approval: Academic Admin approves bonafide."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Internship"
    )
    res = bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    assert res.status == "approved"


def test_br_tc_022():
    """BR-TC-022 | OA-BR-22 download-refused-before-approval: Cannot download when pending."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Internship"
    )
    assert not sm.can_download_bonafide(req.status)


def test_br_tc_023():
    """BR-TC-023 | OA-BR-22 download-permitted-after-approval: Download succeeds after approval."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Internship"
    )
    bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    cert = bonafide_service.get_downloadable_certificate_data(req.id, requesting_user_id=101)
    assert cert["certificate_code"] is not None


# --- OA-BR-31..34: No-Dues Rules ---
def test_br_tc_031():
    """BR-TC-031 | OA-BR-31 domain-specific-authority: Authority records own domain only."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    rec = nodues_service.record_authority_clearance(
        request_id=req.id, domain="library", actor_kind="librarian", verifier_user_id=601, status="cleared"
    )
    assert rec.status == "cleared"


def test_br_tc_032():
    """BR-TC-032 | OA-BR-31 cross-domain-prohibited: Librarian cannot verify Hostel."""
    with pytest.raises(ActorNotAllowed):
        sm.validate_nodues_authority_action("hostel", sm.LIBRARIAN)


def test_br_tc_033():
    """BR-TC-033 | OA-BR-33 finalization-guard-unresolved: Cannot finalize if any domain pending."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    # All 7 are initially pending
    records = {r.authority_domain: r.status for r in req.authority_records.all()}
    with pytest.raises(GuardFailed):
        sm.validate_nodues_finalization(records, sm.ACADEMIC_ADMIN)


def test_br_tc_034():
    """BR-TC-034 | OA-BR-33 finalization-guard-success: Finalizes when all 7 clear."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    for r in req.authority_records.all():
        r.status = "cleared"
        r.save()
    fin = nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)
    assert fin.status == "cleared"


def test_br_tc_035():
    """BR-TC-035 | OA-BR-34 certificate-download-guard: Released only after finalization."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    assert not sm.can_download_nodues_certificate(req.status)


# --- OA-BR-41..46: Assistantship Rules ---
def test_br_tc_041():
    """BR-TC-041 | OA-BR-41 pg-eligibility-enforced: B.Tech students cannot claim assistantship."""
    with pytest.raises(IneligibleStudent):
        rules.validate_pg_student_eligibility("B.Tech")


def test_br_tc_042():
    """BR-TC-042 | OA-BR-42 dual-supervisor-order: Thesis then TA supervisor verification."""
    st1 = sm.resolve_claim_supervisor_state(sm.CLAIM_SUBMITTED, sm.THESIS_SUPERVISOR)
    assert st1 == sm.CLAIM_THESIS_VERIFIED
    st2 = sm.resolve_claim_supervisor_state(st1, sm.TA_SUPERVISOR)
    assert st2 == sm.CLAIM_SUPERVISORS_VERIFIED


def test_br_tc_043():
    """BR-TC-043 | OA-BR-43 department-review-prerequisite: Cannot forward before dual verification."""
    with pytest.raises(GuardFailed):
        sm.validate_claim_department_forward(sm.CLAIM_THESIS_VERIFIED, sm.DEPARTMENT_ADMIN)


def test_br_tc_044():
    """BR-TC-044 | OA-BR-44 hod-assistantship-decision: HoD approves forwarded claim."""
    sm.validate_claim_hod_decision(sm.CLAIM_DEPARTMENT_FORWARDED, sm.HOD, sm.CLAIM_APPROVED)


def test_br_tc_045():
    """BR-TC-045 | OA-BR-45 stipend-processing-prerequisite: Cannot disburse unapproved claim."""
    with pytest.raises(GuardFailed):
        sm.validate_stipend_disbursement(sm.CLAIM_DEPARTMENT_FORWARDED, sm.ACADEMIC_ADMIN)


# --- OA-BR-61..63: Graduate Seminars ---
def test_br_tc_061():
    """BR-TC-061 | OA-BR-61 pg-seminar-eligibility: UG students cannot request seminar."""
    with pytest.raises(IneligibleStudent):
        rules.validate_pg_student_eligibility("B.Tech")


def test_br_tc_062():
    """BR-TC-062 | OA-BR-62 seminar-scheduling-authority: Dept Admin schedules directly."""
    sm.validate_seminar_schedule(sm.SEMINAR_REQUESTED, sm.DEPARTMENT_ADMIN)


def test_br_tc_063():
    """BR-TC-063 | OA-BR-63 seminar-visibility: Scheduled seminars viewable by PG and faculty."""
    from modules.oap.selectors import scoping

    class MockFaculty:
        user_id = 501
        permissions = frozenset(["oap.seminar.view"])
        def has_permission(self, p): return p in self.permissions

    GraduateSeminarRequest.objects.create(
        user_id=101, student_name="Alice", programme="PG", department="CSE",
        topic="AI in Healthcare", proposed_date=datetime.date(2026, 12, 10),
        status="scheduled", scheduled_date=datetime.datetime(2026, 12, 10, 14, 0)
    )
    qs = scoping.scoped_seminars(MockFaculty())
    assert qs.filter(topic="AI in Healthcare").exists()
