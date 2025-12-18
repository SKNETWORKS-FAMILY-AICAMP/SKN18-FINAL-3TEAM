from django.urls import path

from .views import ChatView, ChatbotHealthView, DeleteActiveChatView

urlpatterns = [
    path("", ChatView.as_view(), name="chatbot-chat"),
    path("delete/", DeleteActiveChatView.as_view(), name="chatbot-delete"),
]
