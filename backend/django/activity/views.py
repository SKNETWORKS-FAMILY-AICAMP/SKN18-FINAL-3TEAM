from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView

from .models import WatchingHistory, SearchHistory
from .serializers import (
    WatchingHistorySerializer,
    WatchingHistoryCreateSerializer,
    SearchHistorySerializer,
    SearchHistoryCreateSerializer,
)


# ============================================
# 검색 기록 API
# ============================================

class SearchHistoryListView(ListAPIView):
    """
    내 검색 기록 조회 API

    GET /api/activity/search-logs/
    - 로그인한 사용자의 검색 기록 목록 조회
    - 최신순 정렬
    """
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class SearchHistoryCreateView(CreateAPIView):
    """
    검색 기록 적재 API

    POST /api/activity/search-logs/
    - 검색어 저장
    - request body: {"search_query": "검색어"}
    """
    serializer_class = SearchHistoryCreateSerializer
    permission_classes = [IsAuthenticated]

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
# 시청 기록 API
# ============================================

class WatchingHistoryListView(ListAPIView):
    """
    내 시청 기록 조회 API

    GET /api/activity/watch-logs/
    - 로그인한 사용자의 시청 기록 목록 조회
    - 최신순 정렬
    """
    serializer_class = WatchingHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WatchingHistory.objects.filter(user=self.request.user).select_related('video').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class WatchingHistoryCreateView(CreateAPIView):
    """
    시청 기록 적재 API

    POST /api/activity/watch-logs/
    - 시청 기록 저장 (영상 ID, 시청 위치, 태그)
    - request body: {"video": 1, "watched_seconds": 120, "tags": ["역사", "조선시대"]}
    """
    serializer_class = WatchingHistoryCreateSerializer
    permission_classes = [IsAuthenticated]

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
