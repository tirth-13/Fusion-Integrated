from rest_framework import serializers

class ELMDataSerializer(serializers.Serializer):
    data = serializers.JSONField()
