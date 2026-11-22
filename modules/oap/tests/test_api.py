"""Integration API tests for OAP.

Tested with isolated test DB and stub_iam fixtures from conftest.
"""
import datetime
import pytest
from rest_framework.test import APIClient

from conftest import make_session
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

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=101, permissions=(), kind="student", active_role="student", user_ref=None):
    users_dict = {}
    if user_ref:
        users_dict[user_id] = user_ref(user_id, programme="PG", department="CSE")
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=active_role,
            modules=("oap",),
            permissions=permissions,
        ),
        users=users_dict,
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-tok")
    return c


# ==============================================================================
# LEAVE APPLICATION TESTS
# ==============================================================================

def test_student_submit_and_view_leave(stub_iam, user_ref):
    c = _auth_client(stub_iam, user_id=1001, permissions=("oap.leave.apply", "oap.leave.view_self"), user_ref=user_ref)

    # 1. Submit leave
    payload = {
        "leave_type": "casual",
        "start_date": "2026-11-25",
        "end_date": "2026-11-28",
        "reason": "Family function",
    }
    resp = c.post("/api/v1/oap/leaves", payload, format="json")
    assert resp.status_code == 201
    leave_id = resp.json()["id"]
    assert resp.json()["status"] == "submitted"

    # 2. View leaves
    get_resp = c.get("/api/v1/oap/leaves")
    assert get_resp.status_code == 200
    rows = get_resp.json()["results"]
    assert len(rows) == 1
    assert rows[0]["id"] == leave_id


def test_hod_approve_leave(stub_iam, user_ref):
    # Setup leave submitted by student 1001
    app = LeaveApplication.objects.create(
        user_id=1001,
        student_name="Student One",
        department="CSE",
        leave_type="casual",
        start_date=datetime.date(2026, 11, 25),
        end_date=datetime.date(2026, 11, 28),
        reason="Family function",
        status="submitted",
    )

    # HoD client
    hod_c = _auth_client(
        stub_iam,
        user_id=901,
        permissions=("oap.leave.view", "oap.leave.decide"),
        kind="faculty",
        active_role="hod",
        user_ref=user_ref,
    )

    dec_resp = hod_c.post(f"/api/v1/oap/leaves/{app.id}/decide", {"decision": "approve", "remarks": "Approved"}, format="json")
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "approved"
    assert dec_resp.json()["hod_user_id"] == 901


# ==============================================================================
# BONAFIDE CERTIFICATE TESTS
# ==============================================================================

def test_bonafide_lifecycle_and_download_guard(stub_iam, user_ref):
    student_c = _auth_client(
        stub_iam,
        user_id=1002,
        permissions=("oap.bonafide.request", "oap.bonafide.view_self", "oap.bonafide.download"),
        user_ref=user_ref,
    )

    # 1. Student requests
    resp = student_c.post("/api/v1/oap/bonafide", {"purpose": "Passport application"}, format="json")
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    # 2. Attempt download before approval -> fails (OA-BR-22)
    dl_resp = student_c.get(f"/api/v1/oap/bonafide/{req_id}/download")
    assert dl_resp.status_code == 409

    # 3. Academic Admin approves
    admin_c = _auth_client(
        stub_iam,
        user_id=801,
        permissions=("oap.bonafide.view", "oap.bonafide.decide"),
        kind="staff",
        active_role="academic_admin",
        user_ref=user_ref,
    )
    appr_resp = admin_c.post(f"/api/v1/oap/bonafide/{req_id}/decide", {"decision": "approve", "remarks": "Verified records"}, format="json")
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"

    # 4. Student downloads approved certificate
    dl_resp2 = student_c.get(f"/api/v1/oap/bonafide/{req_id}/download")
    assert dl_resp2.status_code == 200
    assert "certificate_code" in dl_resp2.json()


# ==============================================================================
# NO-DUES CLEARANCE TESTS
# ==============================================================================

def test_nodues_parallel_routing_and_finalization_guard(stub_iam, user_ref):
    student_c = _auth_client(
        stub_iam,
        user_id=1003,
        permissions=("oap.nodues.request", "oap.nodues.view_self", "oap.nodues.download"),
        user_ref=user_ref,
    )

    # 1. Initiate No-Dues
    resp = student_c.post("/api/v1/oap/no-dues", {}, format="json")
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    # Check that all 7 mandatory domain records were created
    records = NoDuesAuthorityRecord.objects.filter(request_id=req_id)
    assert records.count() == 7
    domains = set(records.values_list("authority_domain", flat=True))
    assert domains == {"library", "hostel", "mess", "department", "lab", "academic", "student_section"}

    # 2. Academic Admin tries to finalize while pending -> 409 (OA-BR-33)
    admin_c = _auth_client(
        stub_iam,
        user_id=801,
        permissions=("oap.nodues.view", "oap.nodues.finalize"),
        kind="staff",
        active_role="academic_admin",
        user_ref=user_ref,
    )
    fin_fail = admin_c.post(f"/api/v1/oap/no-dues/{req_id}/finalize", {}, format="json")
    assert fin_fail.status_code == 409

    # 3. Authorities record clearances
    for d in domains:
        rec = NoDuesAuthorityRecord.objects.get(request_id=req_id, authority_domain=d)
        rec.status = "cleared"
        rec.save()

    # 4. Academic Admin finalizes successfully
    fin_ok = admin_c.post(f"/api/v1/oap/no-dues/{req_id}/finalize", {"remarks": "All 7 cleared"}, format="json")
    assert fin_ok.status_code == 200
    assert fin_ok.json()["status"] == "cleared"

    # 5. Student downloads certificate
    dl = student_c.get(f"/api/v1/oap/no-dues/{req_id}/download")
    assert dl.status_code == 200
    assert "certificate_code" in dl.json()


# ==============================================================================
# ASSISTANTSHIP & ASSIGNMENT TESTS
# ==============================================================================

def test_assistantship_full_progression(stub_iam, user_ref):
    # Setup assignments by Dept Admin
    SupervisorAssignment.objects.create(
        student_user_id=1004,
        thesis_supervisor_user_id=501,
        department="CSE",
        assigned_by_user_id=701,
        is_active=True,
    )
    TAAssignment.objects.create(
        student_user_id=1004,
        course_code="CS301",
        ta_supervisor_user_id=502,
        department="CSE",
        assigned_by_user_id=701,
        is_active=True,
    )

    # 1. PG Student submits claim
    pg_c = _auth_client(
        stub_iam,
        user_id=1004,
        permissions=("oap.assistantship.claim", "oap.assistantship.view_self"),
        kind="student",
        active_role="pg_student",
        user_ref=user_ref,
    )
    claim_resp = pg_c.post(
        "/api/v1/oap/assistantships",
        {"claim_month": 11, "claim_year": 2026, "stipend_amount": 12400.00},
        format="json",
    )
    assert claim_resp.status_code == 201
    claim_id = claim_resp.json()["id"]

    # 2. Thesis Supervisor verifies
    sup_c1 = _auth_client(
        stub_iam,
        user_id=501,
        permissions=("oap.assistantship.verify",),
        kind="faculty",
        user_ref=user_ref,
    )
    v1 = sup_c1.post(f"/api/v1/oap/assistantships/{claim_id}/verify", {"role_type": "thesis"}, format="json")
    assert v1.status_code == 200
    assert v1.json()["status"] == "thesis_verified"

    # 3. TA Supervisor verifies
    sup_c2 = _auth_client(
        stub_iam,
        user_id=502,
        permissions=("oap.assistantship.verify",),
        kind="faculty",
        user_ref=user_ref,
    )
    v2 = sup_c2.post(f"/api/v1/oap/assistantships/{claim_id}/verify", {"role_type": "ta"}, format="json")
    assert v2.status_code == 200
    assert v2.json()["status"] == "supervisors_verified"

    # 4. Dept Admin reviews and forwards
    dept_c = _auth_client(
        stub_iam,
        user_id=701,
        permissions=("oap.assistantship.forward",),
        kind="staff",
        active_role="department_admin",
        user_ref=user_ref,
    )
    fwd = dept_c.post(f"/api/v1/oap/assistantships/{claim_id}/forward", {"remarks": "Forwarded"}, format="json")
    assert fwd.status_code == 200
    assert fwd.json()["status"] == "department_forwarded"

    # 5. HoD approves
    hod_c = _auth_client(
        stub_iam,
        user_id=901,
        permissions=("oap.assistantship.decide",),
        kind="faculty",
        active_role="hod",
        user_ref=user_ref,
    )
    dec = hod_c.post(f"/api/v1/oap/assistantships/{claim_id}/decide", {"decision": "approve"}, format="json")
    assert dec.status_code == 200
    assert dec.json()["status"] == "approved"

    # 6. Academic Admin disburses stipend
    acad_c = _auth_client(
        stub_iam,
        user_id=801,
        permissions=("oap.stipend.process",),
        kind="staff",
        active_role="academic_admin",
        user_ref=user_ref,
    )
    disb = acad_c.post(f"/api/v1/oap/assistantships/{claim_id}/disburse", {}, format="json")
    assert disb.status_code == 200
    assert disb.json()["status"] == "disbursed"
    assert disb.json()["stipend_disbursed"] is True


# ==============================================================================
# GRADUATE SEMINAR TESTS
# ==============================================================================

def test_seminar_request_and_schedule(stub_iam, user_ref):
    # 1. PG Student requests seminar
    pg_c = _auth_client(
        stub_iam,
        user_id=1005,
        permissions=("oap.seminar.request", "oap.seminar.view"),
        kind="student",
        active_role="pg_student",
        user_ref=user_ref,
    )
    req = pg_c.post(
        "/api/v1/oap/seminars",
        {
            "topic": "Graph Neural Networks for Microgrids",
            "proposed_date": "2026-12-05",
            "abstract": "Presentation on novel GNN architectures.",
        },
        format="json",
    )
    assert req.status_code == 201
    sem_id = req.json()["id"]
    assert req.json()["status"] == "requested"

    # 2. Dept Admin schedules
    dept_c = _auth_client(
        stub_iam,
        user_id=701,
        permissions=("oap.seminar.manage",),
        kind="staff",
        active_role="department_admin",
        user_ref=user_ref,
    )
    sched = dept_c.post(
        f"/api/v1/oap/seminars/{sem_id}/schedule",
        {
            "scheduled_date": "2026-12-08T14:00:00Z",
            "venue": "Seminar Hall 2",
        },
        format="json",
    )
    assert sched.status_code == 200
    assert sched.json()["status"] == "scheduled"
    assert sched.json()["venue"] == "Seminar Hall 2"


# ==============================================================================
# CONTRACTS TEST
# ==============================================================================

def test_oap_contracts():
    from modules.oap import contracts

    # Leave contract
    LeaveApplication.objects.create(
        user_id=2001,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=2),
        reason="Test",
        status="approved",
    )
    leaves = contracts.get_student_leaves([2001, 2002])
    assert len(leaves[2001]) == 1
    assert leaves[2001][0].status == "approved"
    assert leaves[2002] == []

    # No dues contract
    NoDuesRequest.objects.create(
        user_id=2001,
        status="cleared",
        certificate_code="CERT-123",
    )
    nd = contracts.get_student_no_dues_status([2001, 2002])
    assert nd[2001].is_cleared is True
    assert nd[2001].certificate_code == "CERT-123"
    assert nd[2002].is_cleared is False
