from rest_framework import serializers
from .models import Comment, Reply, Likes


class CommentSerializer(serializers.ModelSerializer):
    """댓글 조회용 serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'user',
            'user_email',
            'user_nickname',
            'video',
            'video_title',
            'comment_content',
            'comment_likes_count',
            'replies_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'comment_likes_count']

    def get_replies_count(self, obj):
        return obj.replies.count()


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 작성용 serializer"""

    class Meta:
        model = Comment
        fields = ['comment_content']

    def create(self, validated_data):
        # user와 video는 view에서 설정
        return super().create(validated_data)


class ReplySerializer(serializers.ModelSerializer):
    """답글 조회용 serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    comment_id = serializers.IntegerField(source='comment.id', read_only=True)

    class Meta:
        model = Reply
        fields = [
            'id',
            'comment',
            'comment_id',
            'user',
            'user_email',
            'user_nickname',
            'reply_content',
            'parent_reply',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'comment']


class ReplyCreateSerializer(serializers.ModelSerializer):
    """답글 작성용 serializer"""

    class Meta:
        model = Reply
        fields = ['reply_content', 'parent_reply']
        extra_kwargs = {
            'parent_reply': {'required': False}
        }

    def create(self, validated_data):
        # user와 comment는 view에서 설정
        return super().create(validated_data)


class LikesSerializer(serializers.ModelSerializer):
    """좋아요 조회용 serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = Likes
        fields = [
            'id',
            'user',
            'user_email',
            'user_nickname',
            'target_type',
            'target_id',
            'video',
            'comment',
            'reply',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user']

    def get_target_type(self, obj):
        if obj.video:
            return 'video'
        elif obj.comment:
            return 'comment'
        elif obj.reply:
            return 'reply'
        return None

    def get_target_id(self, obj):
        if obj.video:
            return obj.video.id
        elif obj.comment:
            return obj.comment.id
        elif obj.reply:
            return obj.reply.id
        return None


class UserActivitySerializer(serializers.Serializer):
    """사용자 커뮤니티 활동 내역 serializer"""
    comments = CommentSerializer(many=True, read_only=True)
    replies = ReplySerializer(many=True, read_only=True)
    likes = LikesSerializer(many=True, read_only=True)
