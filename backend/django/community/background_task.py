# community/tasks.py
import os
from celery import shared_task
from django.contrib.auth import get_user_model
from backend.langgraph_structure1.graph import create_graph_flow
from .models import Comment, Reply

BOT_EMAIL = os.environ.get("BOT_EMAIL")
User = get_user_model()

@shared_task
def generate_reply_for_comment(comment_id):
    # 댓글 ID로 댓글 객체 가져오기
    comment = Comment.objects.get(id=comment_id)
    app = create_graph_flow()
    state = {"query": comment.comment_content, "tag": "chat"}
    result = app.invoke(state)  # 그래프가 async면 asyncio.run(app.ainvoke(state))
    answer = result.get("final_answer") or ""
    # 시스템/봇 계정이 있으면 지정, 없으면 None
    bot_user = User.objects.filter(email=BOT_EMAIL).first() if BOT_EMAIL else None
    Reply.objects.create(
        user=bot_user,
        comment=comment,
        reply_content=answer,
    )
