"""DRF Serializers for OAP.

All write serializers use explicit allow-lists to protect internal fields.
"""
from rest_framework import serializers

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    GraduateSeminarRequest,
    LeaveApplication,
    NoDuesAuthorityRecord,
    NoDuesRequest,
    NotificationOutbox,
    SeminarScheduleLog,
    SupervisorAssignment,
    TAAssignment,
)


# ==============================================================================
# LEAVE SERIALIZERS
# ==============================================================================

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "student_name",
            "programme",
            "department",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "supporting_document",
            "status",
            "hod_user_id",
            "decision_date",
            "remarks",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveApplicationSubmitSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LeaveApplication.LEAVE_TYPES, default="casual")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    supporting_document = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# ==============================================================================
# BONAFIDE SERIALIZERS
# ==============================================================================

class BonafideRequestSerializer(serializers.ModelSerializer):
    is_downloadable = serializers.SerializerMethodField()

    class Meta:
        model = BonafideRequest
        fields = (
            "id",
            "user_id",
            "student_name",
            "programme",
            "department",
            "purpose",
            "status",
            "verified_by_user_id",
            "decision_date",
            "remarks",
            "certificate_code",
            "is_downloadable",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_downloadable(self, obj) -> bool:
        return obj.status == BonafideRequest.STATUS_APPROVED


class BonafideRequestSubmitSerializer(serializers.Serializer):
    purpose = serializers.CharField()


class BonafideDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# ==============================================================================
# NO-DUES SERIALIZERS
# ==============================================================================

class NoDuesAuthorityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesAuthorityRecord
        fields = (
            "id",
            "request_id",
            "authority_domain",
            "status",
            "verifier_user_id",
            "verified_at",
            "dues_amount",
            "remarks",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class NoDuesRequestSerializer(serializers.ModelSerializer):
    authority_records = NoDuesAuthorityRecordSerializer(many=True, read_only=True)
    is_downloadable = serializers.SerializerMethodField()

    class Meta:
        model = NoDuesRequest
        fields = (
            "id",
            "user_id",
            "student_name",
            "programme",
            "department",
            "status",
            "finalized_by_user_id",
            "finalized_at",
            "remarks",
            "certificate_code",
            "is_downloadable",
            "authority_records",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_downloadable(self, obj) -> bool:
        return obj.status == NoDuesRequest.STATUS_CLEARED


class NoDuesAuthorityVerifySerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=[d[0] for d in NoDuesAuthorityRecord.DOMAIN_CHOICES])
    status = serializers.ChoiceField(choices=["cleared", "dues_pending"])
    dues_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class NoDuesFinalizeSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# ==============================================================================
# ASSISTANTSHIP & ASSIGNMENT SERIALIZERS
# ==============================================================================

class SupervisorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisorAssignment
        fields = (
            "id",
            "student_user_id",
            "thesis_supervisor_user_id",
            "department",
            "assigned_by_user_id",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "assigned_by_user_id", "is_active", "created_at")


class SupervisorAssignmentCreateSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField()
    thesis_supervisor_user_id = serializers.IntegerField()
    department = serializers.CharField(max_length=80)


class TAAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAAssignment
        fields = (
            "id",
            "student_user_id",
            "course_code",
            "course_name",
            "ta_supervisor_user_id",
            "department",
            "assigned_by_user_id",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "assigned_by_user_id", "is_active", "created_at")


class TAAssignmentCreateSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField()
    course_code = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    course_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    ta_supervisor_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    department = serializers.CharField(max_length=80)


class AssistantshipClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantshipClaim
        fields = (
            "id",
            "user_id",
            "programme",
            "department",
            "claim_month",
            "claim_year",
            "stipend_amount",
            "thesis_supervisor_user_id",
            "ta_supervisor_user_id",
            "thesis_verified",
            "thesis_verified_at",
            "thesis_remarks",
            "ta_verified",
            "ta_verified_at",
            "ta_remarks",
            "dept_forwarded",
            "dept_forwarded_by_user_id",
            "dept_forwarded_at",
            "dept_remarks",
            "hod_decision",
            "hod_user_id",
            "hod_decided_at",
            "hod_remarks",
            "stipend_disbursed",
            "stipend_disbursed_by_user_id",
            "stipend_disbursed_at",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AssistantshipClaimSubmitSerializer(serializers.Serializer):
    claim_month = serializers.IntegerField(min_value=1, max_value=12)
    claim_year = serializers.IntegerField(min_value=2020, max_value=2035)
    stipend_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00, required=False)


class SupervisorVerifySerializer(serializers.Serializer):
    role_type = serializers.ChoiceField(choices=["thesis", "ta"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class DepartmentForwardSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HoDClaimDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class StipendProcessSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# ==============================================================================
# GRADUATE SEMINAR SERIALIZERS
# ==============================================================================

class SeminarScheduleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeminarScheduleLog
        fields = ("id", "action", "actor_user_id", "details", "created_at")
        read_only_fields = fields


class GraduateSeminarRequestSerializer(serializers.ModelSerializer):
    logs = SeminarScheduleLogSerializer(many=True, read_only=True)

    class Meta:
        model = GraduateSeminarRequest
        fields = (
            "id",
            "user_id",
            "student_name",
            "programme",
            "department",
            "topic",
            "abstract",
            "proposed_date",
            "scheduled_date",
            "venue",
            "status",
            "scheduled_by_user_id",
            "scheduled_at",
            "logs",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class GraduateSeminarSubmitSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=255)
    proposed_date = serializers.DateField()
    abstract = serializers.CharField(required=False, allow_blank=True, default="")


class GraduateSeminarScheduleSerializer(serializers.Serializer):
    scheduled_date = serializers.DateTimeField()
    venue = serializers.CharField(max_length=150)


# ==============================================================================
# NOTIFICATIONS SERIALIZER
# ==============================================================================

class NotificationOutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationOutbox
        fields = (
            "id",
            "topic",
            "subject",
            "body",
            "recipient_user_id",
            "sent_at",
            "created_at",
        )
        read_only_fields = fields
