from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView

from .models import WatchingHistory, SearchHistory
from .serializers import (
    WatchingHistorySerializer,
    WatchingHistoryCreateSerializer,
    SearchHistorySerializer,
    SearchHistoryCreateSerializer,
)


# ============================================
# 검색 기록 API (GET + POST)
# ============================================

class SearchHistoryListCreateView(ListCreateAPIView):
    """
    검색 기록 조회/적재 API

    GET /api/activity/search-logs/  - 내 검색 기록 조회
    POST /api/activity/search-logs/ - 검색 기록 적재
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        # GET: 조회용 Serializer, POST: 생성용 Serializer
        if self.request.method == 'POST':
            return SearchHistoryCreateSerializer
        return SearchHistorySerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'data': serializer.data,
                'message': '검색 기록이 저장되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# 시청 기록 API (GET + POST)
# ============================================

class WatchingHistoryListCreateView(ListCreateAPIView):
    """
    시청 기록 조회/적재 API

    GET /api/activity/watch-logs/  - 내 시청 기록 조회
    POST /api/activity/watch-logs/ - 시청 기록 적재
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WatchingHistory.objects.filter(user=self.request.user).select_related('video').order_by('-created_at')

    def get_serializer_class(self):
        # GET: 조회용 Serializer, POST: 생성용 Serializer
        if self.request.method == 'POST':
            return WatchingHistoryCreateSerializer
        return WatchingHistorySerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'data': serializer.data,
                'message': '시청 기록이 저장되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
