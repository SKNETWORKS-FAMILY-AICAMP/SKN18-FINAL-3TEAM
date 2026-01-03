from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class WatchingHistory(models.Model):
    """
    시청 기록 관리 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: watching_history
    """
    # id는 Django 기본 pk 사용
    video = models.ForeignKey(
        'video.Video',
        on_delete=models.CASCADE,
        db_column='video_id',
        related_name='watch_histories',
        verbose_name='영상'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='watch_histories',
        verbose_name='사용자'
    )
    tags = models.TextField(
        blank=True,
        null=True,
        verbose_name='태그'
    )
    video_keyword = models.TextField(
        blank=True,
        null=True,
        verbose_name='영상 키워드'
    )
    recommended_keyword = models.TextField(
        blank=True,
        null=True,
        verbose_name='추천 키워드'
    )
    watched_seconds = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='시청 위치(초)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='시청일'
    )

    class Meta:
        db_table = 'watching_history'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['-created_at']
        verbose_name = '시청 기록'
        verbose_name_plural = '시청 기록들'

    def __str__(self):
        return f"{self.user.display_name} watched {self.video.title}"


class SearchHistory(models.Model):
    """
    검색 기록 테이블

    init.sql에서 테이블 생성 (managed=False)
    Django는 데이터 읽기/쓰기만 담당

    init.sql 테이블: search_history
    """
    # id는 Django 기본 pk 사용
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='search_histories',
        verbose_name='사용자'
    )
    search_query = models.TextField(
        verbose_name='검색어'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='검색일'
    )

    class Meta:
        db_table = 'search_history'
        managed = False  # init.sql에서 테이블 생성
        ordering = ['-created_at']
        verbose_name = '검색 기록'
        verbose_name_plural = '검색 기록들'

    def __str__(self):
        return f"{self.user.display_name}: {self.search_query}"
