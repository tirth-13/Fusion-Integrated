from rest_framework import viewsets
from .serializers import ELMDataSerializer

class ELMDataViewSet(viewsets.ModelViewSet):
    serializer_class = ELMDataSerializer
    queryset = []  # This will be populated with actual data
