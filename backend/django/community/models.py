from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Comment(models.Model):
    """
    댓글 관리 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: comment
    """
    # id는 Django 기본 pk 사용
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='comments',
        verbose_name='작성자'
    )
    video = models.ForeignKey(
        'video.Video',
        on_delete=models.CASCADE,
        db_column='video_id',
        related_name='comments',
        verbose_name='영상'
    )
    comment_content = models.TextField(
        verbose_name='댓글 내용'
    )
    comment_likes_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='좋아요 수'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일'
    )

    class Meta:
        db_table = 'comment'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['-created_at']
        verbose_name = '댓글'
        verbose_name_plural = '댓글들'

    def __str__(self):
        return f"{self.user.display_name}: {self.comment_content[:30]}"


class Reply(models.Model):
    """
    답글 관리 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: reply
    """
    # id는 Django 기본 pk 사용
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        db_column='comment_id',
        related_name='replies',
        verbose_name='댓글'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='replies',
        verbose_name='작성자'
    )
    reply_content = models.TextField(
        verbose_name='답글 내용'
    )
    parent_reply = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='parent_reply_id',
        related_name='child_replies',
        verbose_name='부모 답글'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일'
    )

    class Meta:
        db_table = 'reply'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['created_at']
        verbose_name = '답글'
        verbose_name_plural = '답글들'

    def __str__(self):
        return f"{self.user.display_name}: {self.reply_content[:30]}"


class Likes(models.Model):
    """
    좋아요 관리 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: likes
    제약조건: video_id, comment_id, reply_id 중 정확히 하나만 NOT NULL
    """
    # id는 Django 기본 pk 사용
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='likes',
        verbose_name='사용자'
    )
    video = models.ForeignKey(
        'video.Video',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='video_id',
        related_name='likes',
        verbose_name='영상'
    )
    comment = models.ForeignKey(
        Comment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='comment_id',
        related_name='likes',
        verbose_name='댓글'
    )
    reply = models.ForeignKey(
        Reply,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='reply_id',
        related_name='likes',
        verbose_name='답글'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일'
    )

    class Meta:
        db_table = 'likes'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['-created_at']
        verbose_name = '좋아요'
        verbose_name_plural = '좋아요들'
        # 제약조건은 init.sql에서 정의됨 (likes_one_target_only)

    def __str__(self):
        target = self.video or self.comment or self.reply
        return f"{self.user.display_name} likes {target}"
