from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator


class Video(models.Model):
    """
    영상 관리 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: video
    """
    # id는 Django 기본 pk 사용
    title = models.CharField(
        max_length=255,
        verbose_name='영상 제목'
    )
    video_url = models.TextField(
        verbose_name='영상 URL'
    )
    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='업로드일'
    )
    tags = ArrayField(
        models.TextField(),
        blank=True,
        null=True,
        verbose_name='태그'
    )
    likes_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='좋아요 수'
    )
    comments_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='댓글 수'
    )

    class Meta:
        db_table = 'video'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['-upload_date']
        verbose_name = '영상'
        verbose_name_plural = '영상들'

    def __str__(self):
        return self.title
