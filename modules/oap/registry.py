"""OAP module registry, navigation items, permissions, and role grants.

What the server tells the shell about this module (ADR-0010).
"""
MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "GraduationCap",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student Nav Items ----------------------------------------------------
    {
        "code": "oap.leaves",
        "label": "My Leaves",
        "icon": "CalendarBlank",
        "to": "/oap/leaves",
        "required_permission": "oap.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "oap.bonafide",
        "label": "Bonafide Certificate",
        "icon": "Certificate",
        "to": "/oap/bonafide",
        "required_permission": "oap.bonafide.view_self",
        "sort_order": 20,
    },
    {
        "code": "oap.nodues",
        "label": "No-Dues Clearance",
        "icon": "CheckSquare",
        "to": "/oap/no-dues",
        "required_permission": "oap.nodues.view_self",
        "sort_order": 30,
    },
    {
        "code": "oap.assistantships",
        "label": "Assistantship Claims",
        "icon": "Money",
        "to": "/oap/assistantships",
        "required_permission": "oap.assistantship.view_self",
        "sort_order": 40,
    },
    {
        "code": "oap.seminars",
        "label": "Graduate Seminars",
        "icon": "Presentation",
        "to": "/oap/seminars",
        "required_permission": "oap.seminar.view",
        "sort_order": 50,
    },
    # -- HoD Nav Items --------------------------------------------------------
    {
        "code": "oap.hod.leaves",
        "label": "Leave Approvals",
        "icon": "CalendarCheck",
        "to": "/oap/hod-leaves",
        "required_permission": "oap.leave.decide",
        "sort_order": 60,
    },
    {
        "code": "oap.hod.claims",
        "label": "Assistantship Approvals",
        "icon": "Stamp",
        "to": "/oap/hod-assistantships",
        "required_permission": "oap.assistantship.decide",
        "sort_order": 70,
    },
    # -- Academic Administrator Nav Items -------------------------------------
    {
        "code": "oap.admin.bonafide",
        "label": "Bonafide Approvals",
        "icon": "Certificate",
        "to": "/oap/admin-bonafide",
        "required_permission": "oap.bonafide.decide",
        "sort_order": 80,
    },
    {
        "code": "oap.admin.nodues",
        "label": "No-Dues Finalization",
        "icon": "FileCheck",
        "to": "/oap/admin-nodues",
        "required_permission": "oap.nodues.finalize",
        "sort_order": 90,
    },
    {
        "code": "oap.admin.stipend",
        "label": "Stipend Processing",
        "icon": "CurrencyInr",
        "to": "/oap/admin-stipend",
        "required_permission": "oap.stipend.process",
        "sort_order": 100,
    },
    # -- Authority Verifier Nav Items -----------------------------------------
    {
        "code": "oap.authority.nodues",
        "label": "Domain No-Dues",
        "icon": "ClipboardCheck",
        "to": "/oap/authority-nodues",
        "required_permission": "oap.nodues.verify",
        "sort_order": 110,
    },
    # -- Department Administrator Nav Items -----------------------------------
    {
        "code": "oap.dept.assignments",
        "label": "Supervisor & TA Assignments",
        "icon": "Users",
        "to": "/oap/dept-assignments",
        "required_permission": "oap.assignment.manage",
        "sort_order": 120,
    },
]

PERMISSIONS = [
    ("oap.leave.apply", "Submit leave applications"),
    ("oap.leave.view_self", "View own leave applications"),
    ("oap.leave.view", "View department or all leave applications"),
    ("oap.leave.decide", "Approve or reject leave applications"),
    ("oap.bonafide.request", "Request bonafide certificates"),
    ("oap.bonafide.view_self", "View own bonafide requests"),
    ("oap.bonafide.view", "View all bonafide requests"),
    ("oap.bonafide.decide", "Approve or reject bonafide requests"),
    ("oap.bonafide.download", "Download approved bonafide certificate"),
    ("oap.nodues.request", "Initiate no-dues clearance"),
    ("oap.nodues.view_self", "View own no-dues progress"),
    ("oap.nodues.view", "View all no-dues requests"),
    ("oap.nodues.verify", "Record domain clearance for no-dues"),
    ("oap.nodues.finalize", "Finalize no-dues clearance"),
    ("oap.nodues.download", "Download finalized no-dues certificate"),
    ("oap.assistantship.claim", "Submit assistantship claims"),
    ("oap.assistantship.view_self", "View own assistantship claims"),
    ("oap.assistantship.view", "View assistantship claims"),
    ("oap.assistantship.verify", "Verify assistantship claims as supervisor"),
    ("oap.assistantship.forward", "Review and forward claims by department"),
    ("oap.assistantship.decide", "Approve or reject assistantship claims"),
    ("oap.stipend.process", "Process stipend disbursement"),
    ("oap.assignment.manage", "Record thesis supervisor and TA assignments"),
    ("oap.assignment.view", "View thesis supervisor and TA assignments"),
    ("oap.seminar.request", "Request graduate seminar scheduling"),
    ("oap.seminar.manage", "Schedule and log graduate seminars"),
    ("oap.seminar.view", "View graduate seminar schedules"),
    ("oap.notification.view_self", "View OAP notifications"),
]

SYSTEM_PERMISSIONS = [
    "oap.notification.view_self",
]

_STUDENT = [
    "oap.leave.apply",
    "oap.leave.view_self",
    "oap.bonafide.request",
    "oap.bonafide.view_self",
    "oap.bonafide.download",
    "oap.nodues.request",
    "oap.nodues.view_self",
    "oap.nodues.download",
    "oap.notification.view_self",
]

_PG_STUDENT = [
    *_STUDENT,
    "oap.assistantship.claim",
    "oap.assistantship.view_self",
    "oap.seminar.request",
    "oap.seminar.view",
    "oap.assignment.view",
]

_FACULTY = [
    "oap.assistantship.verify",
    "oap.seminar.view",
    "oap.assignment.view",
    "oap.notification.view_self",
]

_HOD = [
    "oap.leave.view",
    "oap.leave.decide",
    "oap.assistantship.view",
    "oap.assistantship.decide",
    "oap.seminar.view",
    "oap.assignment.view",
    "oap.notification.view_self",
]

_DEPT_ADMIN = [
    "oap.assistantship.view",
    "oap.assistantship.forward",
    "oap.assignment.manage",
    "oap.assignment.view",
    "oap.seminar.manage",
    "oap.seminar.view",
    "oap.leave.view",
    "oap.notification.view_self",
]

_ACAD_ADMIN = [
    "oap.bonafide.view",
    "oap.bonafide.decide",
    "oap.nodues.view",
    "oap.nodues.finalize",
    "oap.assistantship.view",
    "oap.stipend.process",
    "oap.notification.view_self",
]

_NODUES_AUTHORITY = [
    "oap.nodues.verify",
    "oap.nodues.view",
    "oap.notification.view_self",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "pg_student": _PG_STUDENT,
    "faculty": _FACULTY,
    "hod": _HOD,
    "HOD": _HOD,
    "department_admin": _DEPT_ADMIN,
    "Department Admin": _DEPT_ADMIN,
    "academic_admin": _ACAD_ADMIN,
    "Academic Admin": _ACAD_ADMIN,
    "Dean Academic": _ACAD_ADMIN,
    "librarian": _NODUES_AUTHORITY,
    "Librarian": _NODUES_AUTHORITY,
    "hostel_warden": _NODUES_AUTHORITY,
    "Hostel Warden": _NODUES_AUTHORITY,
    "mess_incharge": _NODUES_AUTHORITY,
    "Mess In-charge": _NODUES_AUTHORITY,
    "lab_supervisor": _NODUES_AUTHORITY,
    "Lab Supervisor": _NODUES_AUTHORITY,
}
