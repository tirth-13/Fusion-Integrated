"""Spec-based tests for Use Cases (OA-UC-01..92).

Generated from docs/09-oap/spec-tests/UC_DESIGN.json per Assignment 9 Prompt B.
Rules:
- test_id and source_id in docstring.
- Covers main flow and alternative flows of use cases.
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


# OA-UC-01 & OA-UC-03: Leave Use Cases
def test_uc_tc_01():
    """UC-TC-01 | OA-UC-01 Main Flow: Student submits leave application."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Family event", supporting_document="doc.pdf"
    )
    assert app.status == "submitted"
    assert app.supporting_document == "doc.pdf"


def test_uc_tc_03():
    """UC-TC-03 | OA-UC-03 Main Flow: HoD reviews and approves leave."""
    app = LeaveApplication.objects.create(
        user_id=101, student_name="Alice", department="CSE", leave_type="casual",
        start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Family event", status="submitted"
    )
    res = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="approve", remarks="Approved")
    assert res.status == "approved"


# OA-UC-11..13: Bonafide Use Cases
def test_uc_tc_11():
    """UC-TC-11 | OA-UC-11 Main Flow: Student requests bonafide certificate."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Education Loan"
    )
    assert req.status == "submitted"


def test_uc_tc_12():
    """UC-TC-12 | OA-UC-12 Main Flow: Academic Admin verifies and approves."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Education Loan"
    )
    res = bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    assert res.status == "approved"


def test_uc_tc_13():
    """UC-TC-13 | OA-UC-13 Main Flow: Student downloads approved bonafide certificate."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Education Loan"
    )
    bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve")
    data = bonafide_service.get_downloadable_certificate_data(req.id, requesting_user_id=101)
    assert "certificate_code" in data


# OA-UC-21..25: No-Dues Use Cases
def test_uc_tc_21():
    """UC-TC-21 | OA-UC-21 Main Flow: Student initiates no-dues clearance."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    assert req.status == "in_progress"
    assert req.authority_records.count() == 7


def test_uc_tc_22():
    """UC-TC-22 | OA-UC-22 Main Flow: Domain authority records clearance."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    rec = nodues_service.record_authority_clearance(
        request_id=req.id, domain="lab", actor_kind="lab_supervisor", verifier_user_id=604, status="cleared"
    )
    assert rec.status == "cleared"


def test_uc_tc_23():
    """UC-TC-23 | OA-UC-23 Main Flow: Academic Admin finalizes no-dues clearance."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    for r in req.authority_records.all():
        r.status = "cleared"
        r.save()
    fin = nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)
    assert fin.status == "cleared"


def test_uc_tc_25():
    """UC-TC-25 | OA-UC-25 Main Flow: Student downloads finalized no-dues certificate."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    for r in req.authority_records.all():
        r.status = "cleared"
        r.save()
    nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)
    cert = nodues_service.get_downloadable_nodues_certificate_data(req.id, requesting_user_id=101)
    assert cert["certificate_code"] is not None


# OA-UC-31..36: Assistantship Use Cases
def test_uc_tc_31():
    """UC-TC-31 | OA-UC-31 Main Flow: PG Student submits assistantship claim."""
    claim = assistantship_service.submit_assistantship_claim(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026, stipend_amount=12400
    )
    assert claim.status == "submitted"


def test_uc_tc_33():
    """UC-TC-33 | OA-UC-33 Main Flow: Dual supervisor verification."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502, status="submitted"
    )
    assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=501, role_type="thesis")
    c = assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=502, role_type="ta")
    assert c.status == "supervisors_verified"


def test_uc_tc_34():
    """UC-TC-34 | OA-UC-34 Main Flow: Dept Admin reviews and forwards claim."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        thesis_verified=True, ta_verified=True, status="supervisors_verified"
    )
    c = assistantship_service.forward_claim_by_department(claim_id=claim.id, dept_admin_user_id=701)
    assert c.status == "department_forwarded"


def test_uc_tc_35():
    """UC-TC-35 | OA-UC-35 Main Flow: HoD approves assistantship claim."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026,
        status="department_forwarded"
    )
    c = assistantship_service.decide_claim_by_hod(claim_id=claim.id, hod_user_id=901, decision="approve")
    assert c.status == "approved"


def test_uc_tc_36():
    """UC-TC-36 | OA-UC-36 Main Flow: Academic Admin processes stipend disbursement."""
    claim = AssistantshipClaim.objects.create(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026, status="approved"
    )
    c = assistantship_service.process_stipend_disbursement(claim_id=claim.id, admin_user_id=801)
    assert c.status == "disbursed"


# OA-UC-41..42: Assignments
def test_uc_tc_41():
    """UC-TC-41 | OA-UC-41 Main Flow: Record thesis supervisor assignment."""
    asgn = assistantship_service.record_thesis_supervisor_assignment(
        student_user_id=101, thesis_supervisor_user_id=501, department="CSE", assigned_by_user_id=701
    )
    assert asgn.thesis_supervisor_user_id == 501


def test_uc_tc_42():
    """UC-TC-42 | OA-UC-42 Main Flow: Record TA assignment."""
    asgn = assistantship_service.record_ta_assignment(
        student_user_id=101, course_code="CS201", ta_supervisor_user_id=502, department="CSE", assigned_by_user_id=701
    )
    assert asgn.course_code == "CS201"


# OA-UC-51..53: Seminars
def test_uc_tc_51():
    """UC-TC-51 | OA-UC-51 Main Flow: Request graduate seminar scheduling."""
    sem = seminar_service.request_seminar(
        user_id=101, student_name="Alice", programme="M.Tech", department="CSE",
        topic="Reinforcement Learning for Robotics", proposed_date=datetime.date(2026, 12, 10)
    )
    assert sem.status == "requested"


def test_uc_tc_53():
    """UC-TC-53 | OA-UC-53 Main Flow: Dept Admin schedules graduate seminar."""
    sem = seminar_service.request_seminar(
        user_id=101, student_name="Alice", programme="M.Tech", department="CSE",
        topic="Reinforcement Learning for Robotics", proposed_date=datetime.date(2026, 12, 10)
    )
    s = seminar_service.schedule_seminar(
        seminar_id=sem.id, dept_admin_user_id=701,
        scheduled_date=datetime.datetime(2026, 12, 12, 15, 0), venue="Audi 1"
    )
    assert s.status == "scheduled"
