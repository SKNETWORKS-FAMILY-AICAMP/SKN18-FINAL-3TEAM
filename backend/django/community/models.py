from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Comment(models.Model):
    """
    댓글 관리 테이블

    init.sql 테이블: comment
    Django가 테이블 생성 및 마이그레이션 관리
    """
    # id는 Django 기본 pk 사용
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
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
        managed = True  # Django가 테이블 생성 및 마이그레이션 관리
        ordering = ['-created_at']
        verbose_name = '댓글'
        verbose_name_plural = '댓글들'

    def __str__(self):
        username = self.user.display_name if self.user else "탈퇴한 사용자"
        return f"{username}: {self.comment_content[:30]}"


class Reply(models.Model):
    """
    답글 관리 테이블

    init.sql 테이블: reply
    Django가 테이블 생성 및 마이그레이션 관리
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
        on_delete=models.SET_NULL,
        null=True,
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
        managed = True  # Django가 테이블 생성 및 마이그레이션 관리
        ordering = ['created_at']
        verbose_name = '답글'
        verbose_name_plural = '답글들'

    def __str__(self):
        username = self.user.display_name if self.user else "탈퇴한 사용자"
        return f"{username}: {self.reply_content[:30]}"


class Likes(models.Model):
    """
    좋아요 관리 테이블

    init.sql 테이블: likes
    Django가 테이블 생성 및 마이그레이션 관리
    제약조건: video_id, comment_id, reply_id 중 최소 하나는 NOT NULL (chk_at_least_one_not_null)
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
        managed = True  # Django가 테이블 생성 및 마이그레이션 관리
        ordering = ['-created_at']
        verbose_name = '좋아요'
        verbose_name_plural = '좋아요들'
        # 제약조건은 init.sql에서 정의됨 (chk_at_least_one_not_null)

    def __str__(self):
        target = self.video or self.comment or self.reply
        username = self.user.display_name if self.user else "알 수 없음"
        return f"{username} likes {target}"
