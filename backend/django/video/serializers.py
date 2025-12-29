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
            'thumbnail_url',
        ]

    def get_comments_count(self, obj):
        """실제 댓글 개수를 DB에서 카운트"""
        from community.models import Comment
        return Comment.objects.filter(video=obj).count()


class VideoDetailSerializer(serializers.ModelSerializer):
    """영상 상세용 Serializer"""
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

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
            'is_liked',
            'thumbnail_url',
        ]

    def get_comments_count(self, obj):
        """실제 댓글 개수를 DB에서 카운트"""
        from community.models import Comment
        return Comment.objects.filter(video=obj).count()

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from community.models import Likes
            return Likes.objects.filter(user=request.user, video=obj).exists()
        return False


class VideoCreateSerializer(serializers.ModelSerializer):
    """영상 생성용 Serializer (관리자용)"""
    # 임시로 video_url 필수 해제 (추후 필수화 시 삭제)  # 수정 필요
    video_url = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Video
        fields = [
            'title',
            'video_url',
            'tags',
            'thumbnail_url',
        ]

