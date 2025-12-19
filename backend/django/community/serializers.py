from rest_framework import serializers
from .models import Comment, Reply, Likes


class CommentUserSerializer(serializers.Serializer):
    """댓글/답글 작성자 정보 serializer"""
    id = serializers.IntegerField(read_only=True)
    nickname = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    profile_image = serializers.CharField(read_only=True, allow_null=True)
    display_name = serializers.CharField(read_only=True)


class CommentSerializer(serializers.ModelSerializer):
    """댓글 조회용 serializer"""
    user = CommentUserSerializer(read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)
    replies_count = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'user',
            'video',
            'video_title',
            'comment_content',
            'comment_likes_count',
            'replies_count',
            'replies',
            'is_liked',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'comment_likes_count']

    def get_replies_count(self, obj):
        return obj.replies.count()

    def get_replies(self, obj):
        """최상위 답글만 가져옴 (parent_reply가 없는 것들)"""
        # ReplySerializer가 아래에 정의되므로 import 필요 없음
        top_level_replies = obj.replies.filter(parent_reply__isnull=True)
        return ReplySerializer(top_level_replies, many=True, context=self.context).data

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 작성용 serializer"""

    class Meta:
        model = Comment
        fields = ['comment_content']

    def create(self, validated_data):
        # user와 video는 view에서 설정
        return super().create(validated_data)


class ReplySerializer(serializers.ModelSerializer):
    """답글 조회용 serializer (재귀적 중첩 지원)"""
    user = CommentUserSerializer(read_only=True)
    comment_id = serializers.IntegerField(source='comment.id', read_only=True)
    comment_content = serializers.CharField(source='comment.comment_content', read_only=True)
    comment_user = CommentUserSerializer(source='comment.user', read_only=True)
    comment_created_at = serializers.DateTimeField(source='comment.created_at', read_only=True)
    video_id = serializers.IntegerField(source='comment.video.id', read_only=True)
    video_title = serializers.CharField(source='comment.video.title', read_only=True)
    child_replies = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Reply
        fields = [
            'id',
            'comment',
            'comment_id',
            'comment_content',
            'comment_user',
            'comment_created_at',
            'video_id',
            'video_title',
            'user',
            'reply_content',
            'parent_reply',
            'child_replies',
            'likes_count',
            'is_liked',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'comment']

    def get_child_replies(self, obj):
        """자식 답글들을 재귀적으로 가져옴"""
        children = obj.child_replies.all()
        return ReplySerializer(children, many=True, context=self.context).data

    def get_likes_count(self, obj):
        """답글 좋아요 수"""
        return obj.likes.count()

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 여부"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class ReplyCreateSerializer(serializers.ModelSerializer):
    """답글 작성용 serializer"""
    # parent_reply는 기본 PrimaryKeyRelatedField를 사용하지만, 0/빈 값이면 None으로 강제
    # to_internal_value에서 미리 정규화해 pk=0 검증 에러를 방지한다.

    def to_internal_value(self, data):
        data = data.copy()
        # 0, "0", "", None => 부모 없음으로 처리
        if data.get('parent_reply') in (0, '0', '', None):
            data['parent_reply'] = None
        return super().to_internal_value(data)

    class Meta:
        model = Reply
        fields = ['reply_content', 'parent_reply']
        extra_kwargs = {
            'parent_reply': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        # user와 comment는 view에서 설정
        return super().create(validated_data)

    def validate_parent_reply(self, value):
        """
        0, 빈 값, null 등을 부모 없음으로 처리.
        실제 존재하는 PK만 유지.
        """
        if not value:
            return None
        return value


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
