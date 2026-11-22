"""OAP database models, partitioned by aggregate."""
from modules.oap.models.assistantships import (
    AssistantshipClaim,
    SupervisorAssignment,
    TAAssignment,
)
from modules.oap.models.bonafide import (
    BonafideRequest,
)
from modules.oap.models.leaves import (
    LeaveApplication,
)
from modules.oap.models.no_dues import (
    NoDuesAuthorityRecord,
    NoDuesRequest,
)
from modules.oap.models.notifications import (
    NotificationOutbox,
)
from modules.oap.models.seminars import (
    GraduateSeminarRequest,
    SeminarScheduleLog,
)

__all__ = [
    "AssistantshipClaim",
    "BonafideRequest",
    "GraduateSeminarRequest",
    "LeaveApplication",
    "NoDuesAuthorityRecord",
    "NoDuesRequest",
    "NotificationOutbox",
    "SeminarScheduleLog",
    "SupervisorAssignment",
    "TAAssignment",
]
