"""Spec-based tests for Functional Requirements (CFR/AFR).

Generated from docs/09-oap/spec-tests/FR_DESIGN.json per Assignment 9 Prompt B.
Rules:
- test_id and source_id in docstring.
- Covers testable CFRs and AFRs without skipping.
"""
import datetime
import pytest

from modules.oap.domain import state_machine as sm
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    GraduateSeminarRequest,
    LeaveApplication,
    NoDuesAuthorityRecord,
    NoDuesRequest,
    NotificationOutbox,
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


# CFR-OAP-001 / AFR-OAP-001, 002: Role-based access control
def test_fr_t01():
    """FR-T01 | AFR-OAP-001 authorized-role access: Authorized student submits leave."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical",
    )
    assert app.id is not None


def test_fr_t02():
    """FR-T02 | AFR-OAP-001 unauthorized-role denial: Student cannot approve leave."""
    from modules.oap.domain.errors import ActorNotAllowed
    with pytest.raises(ActorNotAllowed):
        sm.validate_leave_transition(sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.STUDENT)


# CFR-OAP-002 / AFR-OAP-004..008: Notifications and Reminders
def test_fr_t04():
    """FR-T04 | AFR-OAP-004 submission notification: Outbox enqueued on submission."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical",
    )
    assert NotificationOutbox.objects.filter(recipient_user_id=101, topic="oap.leave.submitted").exists()


def test_fr_t05():
    """FR-T05 | AFR-OAP-005 decision notification: Outbox enqueued on approval."""
    app = LeaveApplication.objects.create(
        user_id=101, student_name="Alice", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical", status="submitted"
    )
    leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="approve")
    assert NotificationOutbox.objects.filter(recipient_user_id=101, topic="oap.leave.approved").exists()


# CFR-OAP-003..005: Leave Management
def test_fr_t09():
    """FR-T09 | AFR-OAP-009 student-leave-submission: Leave record created with submitted status."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical",
    )
    assert app.status == "submitted"


def test_fr_t10():
    """FR-T10 | AFR-OAP-010 optional-supporting-document: Document link retained."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="medical", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical checkup", supporting_document="https://docs.example.com/prescription.pdf"
    )
    assert app.supporting_document == "https://docs.example.com/prescription.pdf"


def test_fr_t13():
    """FR-T13 | AFR-OAP-013 hod-decision-recording: Status transitions to approved."""
    app = LeaveApplication.objects.create(
        user_id=101, student_name="Alice", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 2),
        reason="Medical", status="submitted"
    )
    app = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="approve", remarks="Approved")
    assert app.status == "approved"
    assert app.hod_user_id == 901


# CFR-OAP-006..008: Bonafide Certificates
def test_fr_t16():
    """FR-T16 | AFR-OAP-016 bonafide-request-submission: Student submits bonafide."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Bank Account"
    )
    assert req.status == "submitted"


def test_fr_t19():
    """FR-T19 | AFR-OAP-019 acad-admin-decision: Academic Admin decides request."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Bank Account"
    )
    req = bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    assert req.status == "approved"
    assert req.verified_by_user_id == 801


def test_fr_t21():
    """FR-T21 | AFR-OAP-021 approved-certificate-download: Download permitted when approved."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Bank Account"
    )
    bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    cert = bonafide_service.get_downloadable_certificate_data(req.id, requesting_user_id=101)
    assert cert["certificate_code"] is not None


# CFR-OAP-009..012: No-Dues Clearance
def test_fr_t22():
    """FR-T22 | AFR-OAP-022 nodues-initiation: Student initiates no-dues."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    assert req.status == "in_progress"


def test_fr_t23():
    """FR-T23 | AFR-OAP-023 parallel-routing-seven-domains: 7 domain records created."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    assert req.authority_records.count() == 7


def test_fr_t24():
    """FR-T24 | AFR-OAP-024..028 domain-clearance-recorded: Domain result updated independently."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    rec = nodues_service.record_authority_clearance(
        request_id=req.id, domain="mess", actor_kind="mess_incharge", verifier_user_id=602, status="cleared"
    )
    assert rec.status == "cleared"
    assert req.authority_records.get(authority_domain="library").status == "pending"


def test_fr_t30():
    """FR-T30 | AFR-OAP-030 finalization-all-seven-clear: Finalization sets cleared status."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    for r in req.authority_records.all():
        r.status = "cleared"
        r.save()
    fin = nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)
    assert fin.status == "cleared"


# CFR-OAP-013..018: PG Assistantship Claims
def test_fr_t33():
    """FR-T33 | AFR-OAP-033 assistantship-claim-submission: PG student submits claim."""
    claim = assistantship_service.submit_assistantship_claim(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026, stipend_amount=12400
    )
    assert claim.status == "submitted"


def test_fr_t35():
    """FR-T35 | AFR-OAP-035 dual-supervisor-verifications: Thesis & TA supervisor verification."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502, status="submitted"
    )
    c1 = assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=501, role_type="thesis")
    assert c1.status == "thesis_verified"
    c2 = assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=502, role_type="ta")
    assert c2.status == "supervisors_verified"


def test_fr_t38():
    """FR-T38 | AFR-OAP-038 dept-forwarding: Dept Admin forwards verified claim."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        thesis_verified=True, ta_verified=True, status="supervisors_verified"
    )
    c = assistantship_service.forward_claim_by_department(claim_id=claim.id, dept_admin_user_id=701)
    assert c.status == "department_forwarded"


def test_fr_t39():
    """FR-T39 | AFR-OAP-039 hod-claim-decision: HoD approves claim."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        status="department_forwarded"
    )
    c = assistantship_service.decide_claim_by_hod(claim_id=claim.id, hod_user_id=901, decision="approve")
    assert c.status == "approved"


def test_fr_t41():
    """FR-T41 | AFR-OAP-041 stipend-disbursement: Academic Admin disburses approved claim."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        status="approved"
    )
    c = assistantship_service.process_stipend_disbursement(claim_id=claim.id, admin_user_id=801)
    assert c.status == "disbursed"
    assert c.stipend_disbursed is True


# CFR-OAP-019: Assignments
def test_fr_t43():
    """FR-T43 | AFR-OAP-043 supervisor-assignment-recording: Thesis supervisor recorded."""
    asgn = assistantship_service.record_thesis_supervisor_assignment(
        student_user_id=101, thesis_supervisor_user_id=501, department="CSE", assigned_by_user_id=701
    )
    assert asgn.thesis_supervisor_user_id == 501
    assert asgn.is_active is True


def test_fr_t44():
    """FR-T44 | AFR-OAP-044 ta-assignment-recording: TA assignment recorded."""
    asgn = assistantship_service.record_ta_assignment(
        student_user_id=101, course_code="CS101", ta_supervisor_user_id=502, department="CSE", assigned_by_user_id=701
    )
    assert asgn.course_code == "CS101"
    assert asgn.ta_supervisor_user_id == 502


# CFR-OAP-020..022: Graduate Seminars
def test_fr_t45():
    """FR-T45 | AFR-OAP-045 seminar-request-initiation: PG student initiates seminar request."""
    sem = seminar_service.request_seminar(
        user_id=101, student_name="Alice", programme="Ph.D", department="CSE",
        topic="Neural Architecture Search", proposed_date=datetime.date(2026, 12, 20)
    )
    assert sem.status == "requested"


def test_fr_t47():
    """FR-T47 | AFR-OAP-047 seminar-scheduling: Dept Admin schedules seminar."""
    sem = seminar_service.request_seminar(
        user_id=101, student_name="Alice", programme="Ph.D", department="CSE",
        topic="Neural Architecture Search", proposed_date=datetime.date(2026, 12, 20)
    )
    s = seminar_service.schedule_seminar(
        seminar_id=sem.id, dept_admin_user_id=701,
        scheduled_date=datetime.datetime(2026, 12, 22, 10, 0), venue="Hall C"
    )
    assert s.status == "scheduled"
    assert s.venue == "Hall C"
