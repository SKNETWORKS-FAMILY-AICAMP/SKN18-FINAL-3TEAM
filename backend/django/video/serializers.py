from rest_framework import serializers
from .models import Video


class VideoSerializer(serializers.ModelSerializer):
    """영상 목록용 Serializer"""
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'video_url',
            'upload_date',
            'tags',
            'likes_count',
            'comments_count',
        ]

    def get_comments_count(self, obj):
        """실제 댓글 개수를 DB에서 카운트"""
        from community.models import Comment
        return Comment.objects.filter(video=obj).count()


class VideoDetailSerializer(serializers.ModelSerializer):
    """영상 상세용 Serializer"""
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'video_url',
            'upload_date',
            'tags',
            'likes_count',
            'comments_count',
        ]

    def get_comments_count(self, obj):
        """실제 댓글 개수를 DB에서 카운트"""
        from community.models import Comment
        return Comment.objects.filter(video=obj).count()


class VideoCreateSerializer(serializers.ModelSerializer):
    """영상 생성용 Serializer (관리자용)"""
    
    class Meta:
        model = Video
        fields = [
            'title',
            'video_url',
            'tags',
        ]

