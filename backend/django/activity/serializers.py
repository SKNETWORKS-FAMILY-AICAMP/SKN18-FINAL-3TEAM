from rest_framework import serializers
from .models import WatchingHistory, SearchHistory


class WatchingHistorySerializer(serializers.ModelSerializer):
    """시청 기록 조회용 serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_thumbnail = serializers.CharField(source='video.thumbnail_url', read_only=True)

    class Meta:
        model = WatchingHistory
        fields = [
            'id',
            'video',
            'video_title',
            'video_thumbnail',
            'user',
            'user_email',
            'user_nickname',
            'tags',
            'watched_seconds',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user']


class WatchingHistoryCreateSerializer(serializers.ModelSerializer):
    """시청 기록 적재용 serializer"""

    class Meta:
        model = WatchingHistory
        fields = ['video', 'tags', 'watched_seconds']

    def create(self, validated_data):
        # user는 request.user에서 자동으로 설정
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SearchHistorySerializer(serializers.ModelSerializer):
    """검색 기록 조회용 serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)

    class Meta:
        model = SearchHistory
        fields = [
            'id',
            'user',
            'user_email',
            'user_nickname',
            'search_query',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user']


class SearchHistoryCreateSerializer(serializers.ModelSerializer):
    """검색 기록 적재용 serializer"""

    class Meta:
        model = SearchHistory
        fields = ['search_query']

    def create(self, validated_data):
        # user는 request.user에서 자동으로 설정
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
