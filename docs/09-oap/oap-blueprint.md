# Blueprint: Other Academic Procedures (OAP)

**Module:** Other Academic Procedures (`oap`)  
**Status:** Approved  
**Approver (Student 2):** Approved in writing  
**Date:** 2026-11-22  
**Baseline commit:** `170a7a7`

---

## 1. Domain Model and Aggregates

The OAP module implements role-controlled handling of 5 distinct academic procedures:
1. **Leave Management**: `LeaveApplication` (`oap_leave_application`)
   * States: `draft` -> `submitted` -> `approved` | `rejected`
   * Reviewed & approved/rejected solely by HoD (`OA-BR-11`).
2. **Bonafide Certificates**: `BonafideRequest` (`oap_bonafide_request`)
   * States: `submitted` -> `approved` | `rejected`
   * Verified & approved/rejected solely by Academic Administrator (`OA-BR-21`).
   * Downloadable certificate issued with UUID `certificate_code` only after approval (`OA-BR-22`).
3. **No-Dues Clearance**: `NoDuesRequest` & `NoDuesAuthorityRecord`
   * Central request routes in parallel to **7 mandatory domains**: `library`, `hostel`, `mess`, `department`, `lab`, `academic`, `student_section` (`AFR-OAP-023`).
   * Each domain authority records status (`pending`, `cleared`, `dues_pending`) independently (`OA-BR-31`, `32`).
   * Finalization Guard: Finalized by Academic Administrator **only when all 7 domains record cleared** (`OA-BR-33`).
   * Certificate downloadable only after finalization (`OA-BR-34`).
4. **PG Assistantships & Assignments**:
   * Department Administrator records `SupervisorAssignment` and `TAAssignment` (course/faculty association, `OA-BR-51`).
   * PG students submit monthly claims (`OA-BR-41`).
   * **Dual Supervisor Verification**: Both Thesis Supervisor and TA Supervisor must verify before departmental review (`OA-BR-42`, `52`).
   * Dept Admin reviews and forwards to HoD (`OA-BR-43`).
   * HoD approves or rejects (`OA-BR-44`).
   * Academic Administrator disburses stipend only for HoD-approved claims (`OA-BR-45`).
5. **Graduate Seminars**: `GraduateSeminarRequest` & `SeminarScheduleLog`
   * PG students initiate seminar scheduling requests (`OA-BR-61`).
   * Dept Admin schedules date & venue directly without separate approval stages (`OA-BR-62`).
   * Schedules visible to PG students and faculty (`OA-BR-63`).
6. **Notification Outbox**: `NotificationOutbox` (`oap_notification_outbox`)
   * Reliable transactional outbox delivering system alerts and emails on all lifecycle events (`OA-BR-03`).

---

## 2. API Surface

| Endpoint | Method | Permission | Description |
|---|---|---|---|
| `/api/v1/oap/leaves` | GET, POST | `oap.leave.view_self` / `apply` | List or submit leaves |
| `/api/v1/oap/leaves/<id>/decide` | POST | `oap.leave.decide` | HoD approve or reject leave |
| `/api/v1/oap/bonafide` | GET, POST | `oap.bonafide.view_self` / `request` | List or request bonafide |
| `/api/v1/oap/bonafide/<id>/decide` | POST | `oap.bonafide.decide` | Academic Admin approve/reject |
| `/api/v1/oap/bonafide/<id>/download` | GET | `oap.bonafide.download` | Download approved certificate |
| `/api/v1/oap/no-dues` | GET, POST | `oap.nodues.view_self` / `request` | List or initiate no-dues |
| `/api/v1/oap/no-dues/<id>/verify` | POST | `oap.nodues.verify` | Domain authority records clearance |
| `/api/v1/oap/no-dues/<id>/finalize` | POST | `oap.nodues.finalize` | Academic Admin finalizes no-dues |
| `/api/v1/oap/no-dues/<id>/download` | GET | `oap.nodues.download` | Download finalized certificate |
| `/api/v1/oap/assistantships` | GET, POST | `oap.assistantship.view_self` / `claim` | List or submit assistantship claims |
| `/api/v1/oap/assistantships/<id>/verify` | POST | `oap.assistantship.verify` | Supervisor verification (thesis/ta) |
| `/api/v1/oap/assistantships/<id>/forward` | POST | `oap.assistantship.forward` | Dept Admin review and forward |
| `/api/v1/oap/assistantships/<id>/decide` | POST | `oap.assistantship.decide` | HoD decision |
| `/api/v1/oap/assistantships/<id>/disburse` | POST | `oap.stipend.process` | Academic Admin stipend disbursement |
| `/api/v1/oap/assignments/supervisors` | GET, POST | `oap.assignment.manage` | Manage thesis supervisor assignments |
| `/api/v1/oap/assignments/tas` | GET, POST | `oap.assignment.manage` | Manage TA assignments |
| `/api/v1/oap/seminars` | GET, POST | `oap.seminar.view` / `request` | View schedules or request seminar |
| `/api/v1/oap/seminars/<id>/schedule` | POST | `oap.seminar.manage` | Dept Admin schedules seminar |
| `/api/v1/oap/notifications` | GET | `oap.notification.view_self` | View user notifications |

---

## 3. Public Contracts (`modules/oap/contracts.py`)

All cross-module getters take `Sequence[int]` and return dictionaries (plural by signature):
* `get_student_no_dues_status(user_ids: Sequence[int]) -> dict[int, NoDuesStatusDTO]`
* `get_student_leaves(user_ids: Sequence[int]) -> dict[int, list[StudentLeaveDTO]]`
* `get_student_supervisors(user_ids: Sequence[int]) -> dict[int, StudentSupervisorsDTO]`
