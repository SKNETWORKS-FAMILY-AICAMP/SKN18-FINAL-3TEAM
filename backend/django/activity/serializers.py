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
            'tags',
            'video_keyword',
            'recommended_keyword',
            'watched_seconds',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user']


class WatchingHistoryCreateSerializer(serializers.ModelSerializer):
    """시청 기록 적재용 serializer"""

    class Meta:
        model = WatchingHistory
        fields = [
            'video',
            'tags',
            'video_keyword',
            'recommended_keyword',
            'watched_seconds'
            ]

    def create(self, validated_data):
        def normalize_value(value):
            if value is None:
                return None
            if isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
                return ",".join(items) if items else None
            return value

        for field in ("tags", "video_keyword", "recommended_keyword"):
            if field in validated_data:
                validated_data[field] = normalize_value(validated_data[field])

        # user는 request.user에서 자동으로 설정
        user = self.context['request'].user
        validated_data['user'] = user

        video = validated_data.get('video')
        existing = None
        if video is not None:
            existing = WatchingHistory.objects.filter(
                user=user,
                video=video,
            ).order_by('-created_at').first()

        if existing:
            for field in ("tags", "video_keyword", "recommended_keyword"):
                if field in validated_data and validated_data[field] is not None:
                    setattr(existing, field, validated_data[field])
            if "watched_seconds" in validated_data:
                existing.watched_seconds = validated_data["watched_seconds"]
            existing.save()
            return existing

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
