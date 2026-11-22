"""Spec-based tests for Workflows (BW-OAP-01..09, CW-OAP-01..04).

Generated from docs/09-oap/spec-tests/WF_DESIGN.json per Assignment 9 Prompt B.
Rules:
- test_id and source_id in docstrings.
- Exercises distinct workflow paths end-to-end.
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


def test_wf_tc_01():
    """WF-TC-01 | BW-OAP-01 leave-approved path (CW-OAP-01): Student submit -> HoD approve."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Leave",
    )
    assert app.status == sm.LEAVE_SUBMITTED
    app = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="approve", remarks="Approved")
    assert app.status == sm.LEAVE_APPROVED


def test_wf_tc_02():
    """WF-TC-02 | BW-OAP-02 leave-rejected path (CW-OAP-01): Student submit -> HoD reject."""
    app = leave_service.submit_leave(
        user_id=101, student_name="Alice", programme="UG", department="CSE",
        leave_type="casual", start_date=datetime.date(2026, 12, 1), end_date=datetime.date(2026, 12, 3),
        reason="Leave",
    )
    app = leave_service.decide_leave(leave_id=app.id, hod_user_id=901, decision="reject", remarks="Rejected")
    assert app.status == sm.LEAVE_REJECTED


def test_wf_tc_03():
    """WF-TC-03 | BW-OAP-03 bonafide-approved path (CW-OAP-02): Student request -> Acad Admin approve."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Internship"
    )
    assert req.status == sm.BONAFIDE_SUBMITTED
    req = bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="approve", remarks="OK")
    assert req.status == sm.BONAFIDE_APPROVED
    assert sm.can_download_bonafide(req.status)


def test_wf_tc_04():
    """WF-TC-04 | BW-OAP-04 bonafide-rejected path (CW-OAP-02): Student request -> Acad Admin reject."""
    req = bonafide_service.request_bonafide(
        user_id=101, student_name="Alice", programme="UG", department="CSE", purpose="Internship"
    )
    req = bonafide_service.decide_bonafide(request_id=req.id, admin_user_id=801, decision="reject", remarks="Incomplete")
    assert req.status == sm.BONAFIDE_REJECTED
    assert not sm.can_download_bonafide(req.status)


def test_wf_tc_05():
    """WF-TC-05 | BW-OAP-05 nodues-cleared path (CW-OAP-03): Student initiate -> all 7 clear -> finalize."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    assert req.status == sm.NODUES_IN_PROGRESS
    assert req.authority_records.count() == 7

    for r in req.authority_records.all():
        nodues_service.record_authority_clearance(
            request_id=req.id, domain=r.authority_domain, actor_kind=sm.DOMAIN_AUTHORITY_ACTORS[r.authority_domain],
            verifier_user_id=600, status="cleared"
        )

    req = nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)
    assert req.status == sm.NODUES_CLEARED
    assert sm.can_download_nodues_certificate(req.status)


def test_wf_tc_06():
    """WF-TC-06 | BW-OAP-06 nodues-dues-outstanding path (CW-OAP-03): One domain has dues -> finalization refused."""
    req = nodues_service.initiate_no_dues(user_id=101, student_name="Alice", programme="UG", department="CSE")
    # Library records dues pending
    nodues_service.record_authority_clearance(
        request_id=req.id, domain="library", actor_kind="librarian", verifier_user_id=601, status="dues_pending"
    )
    from core.api.exceptions import ConflictError
    with pytest.raises(ConflictError):
        nodues_service.finalize_no_dues(request_id=req.id, admin_user_id=801)


def test_wf_tc_07():
    """WF-TC-07 | BW-OAP-07 assistantship-approved-and-processed (CW-OAP-04): Complete successful chain."""
    # Setup assignments
    SupervisorAssignment.objects.create(
        student_user_id=101, thesis_supervisor_user_id=501, department="CSE", assigned_by_user_id=701, is_active=True
    )
    TAAssignment.objects.create(
        student_user_id=101, course_code="CS301", ta_supervisor_user_id=502, department="CSE",
        assigned_by_user_id=701, is_active=True
    )
    # 1. Submit claim
    claim = assistantship_service.submit_assistantship_claim(
        user_id=101, programme="M.Tech", department="CSE", claim_month=11, claim_year=2026, stipend_amount=12400
    )
    assert claim.status == sm.CLAIM_SUBMITTED

    # 2. Thesis supervisor verifies
    claim = assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=501, role_type="thesis")
    assert claim.status == sm.CLAIM_THESIS_VERIFIED

    # 3. TA supervisor verifies
    claim = assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=502, role_type="ta")
    assert claim.status == sm.CLAIM_SUPERVISORS_VERIFIED

    # 4. Dept Admin forwards
    claim = assistantship_service.forward_claim_by_department(claim_id=claim.id, dept_admin_user_id=701)
    assert claim.status == sm.CLAIM_DEPARTMENT_FORWARDED

    # 5. HoD approves
    claim = assistantship_service.decide_claim_by_hod(claim_id=claim.id, hod_user_id=901, decision="approve")
    assert claim.status == sm.CLAIM_APPROVED

    # 6. Acad Admin disburses
    claim = assistantship_service.process_stipend_disbursement(claim_id=claim.id, admin_user_id=801)
    assert claim.status == sm.CLAIM_DISBURSED
    assert claim.stipend_disbursed is True


def test_wf_tc_08():
    """WF-TC-08 | BW-OAP-08 assistantship-rejected-by-hod (CW-OAP-04): HoD rejects claim."""
    SupervisorAssignment.objects.create(
        student_user_id=101, thesis_supervisor_user_id=501, department="CSE", assigned_by_user_id=701, is_active=True
    )
    TAAssignment.objects.create(
        student_user_id=101, course_code="CS301", ta_supervisor_user_id=502, department="CSE",
        assigned_by_user_id=701, is_active=True
    )
    claim = assistantship_service.submit_assistantship_claim(
        user_id=101, programme="Ph.D", department="CSE", claim_month=11, claim_year=2026, stipend_amount=12400
    )
    assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=501, role_type="thesis")
    assistantship_service.verify_supervisor_claim(claim_id=claim.id, verifier_user_id=502, role_type="ta")
    assistantship_service.forward_claim_by_department(claim_id=claim.id, dept_admin_user_id=701)
    claim = assistantship_service.decide_claim_by_hod(claim_id=claim.id, hod_user_id=901, decision="reject", remarks="Low attendance")
    assert claim.status == sm.CLAIM_REJECTED


def test_wf_tc_09():
    """WF-TC-09 | BW-OAP-09 graduate-seminar-scheduling: PG student request -> Dept Admin schedule."""
    sem = seminar_service.request_seminar(
        user_id=101, student_name="Alice", programme="Ph.D", department="CSE",
        topic="Efficient LLM Inference", proposed_date=datetime.date(2026, 12, 15)
    )
    assert sem.status == sm.SEMINAR_REQUESTED
    sched = seminar_service.schedule_seminar(
        seminar_id=sem.id, dept_admin_user_id=701,
        scheduled_date=datetime.datetime(2026, 12, 18, 11, 0), venue="Hall A"
    )
    assert sched.status == sm.SEMINAR_SCHEDULED
    assert sched.venue == "Hall A"
