from django.db import models
from django.conf import settings


# 사용자 상담 기록 저장
class ChatSession(models.Model):
    """
    Tracks a chat conversation, initially keyed by an anonymous session and
    later linked to a user once they log in.
    """
    session_key = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="chat_sessions",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_session'
        ordering = ["-created_at"]
        verbose_name = "대화 세션"
        verbose_name_plural = "대화 세션"

    def __str__(self) -> str:
        if self.user:
            return f"{self.user}의 세션"
        return f"익명 세션({self.session_key})"


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "사용자"
        ASSISTANT = "assistant", "어시스턴트"
        SYSTEM = "system", "상담 요약"

    session = models.ForeignKey(
        ChatSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message'
        ordering = ["created_at"]
        verbose_name = "대화 메시지"
        verbose_name_plural = "대화 메시지"

    def __str__(self) -> str:
        return f"{self.get_role_display()}@{self.created_at:%Y-%m-%d %H:%M}"