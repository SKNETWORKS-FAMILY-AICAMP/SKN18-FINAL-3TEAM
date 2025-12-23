from django.urls import path

from .views import (
    ChatQuestionView,
    ChatHistoryView,
    ChatSessionView,
    ChatSessionDeleteView,
    NewSessionView,
    ChatView,
    ChatbotHealthView,
    DeleteActiveChatView,
)

urlpatterns = [
    path("", ChatView.as_view(), name="chatbot-chat"),
    path("new-session/", NewSessionView.as_view(), name="chat-new-session"),
    path("question/", ChatQuestionView.as_view(), name="chat-question"),
    path("history/", ChatHistoryView.as_view(), name="chat-history"),
    path("session/<int:session_id>/", ChatSessionView.as_view(), name="chat-session"),
    path("session/<int:session_id>/delete/", ChatSessionDeleteView.as_view(), name="chat-session-delete"),
    path("delete/", DeleteActiveChatView.as_view(), name="chatbot-delete"),
]
