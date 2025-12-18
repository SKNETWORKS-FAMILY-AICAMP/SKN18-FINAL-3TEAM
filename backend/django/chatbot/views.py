import asyncio
import logging

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, ChatSession
from backend.langgraph_structure1.graph import create_graph_flow

logger = logging.getLogger("chatbot")

def _get_or_create_session_for_user(request, *, create=True):
    """
    인증된 사용자를 위한 ChatSession을 가져온다.
    create=False인 경우에는 존재하지 않으면 None을 반환한다.
    """
    if not request.session.session_key:
        request.session.save()
        logger.info("[chat] generated new session_key=%s", request.session.session_key)

    chat_session = ChatSession.objects.filter(
        session_key=request.session.session_key
    ).first()

    if chat_session is None and create:
        chat_session = ChatSession.objects.create(
            session_key=request.session.session_key,
            user=request.user if request.user.is_authenticated else None,
        )
        logger.info("[chat] created ChatSession id=%s key=%s user=%s", chat_session.id, chat_session.session_key, chat_session.user_id)

    if chat_session and chat_session.user_id is None and request.user.is_authenticated:
        chat_session.user = request.user
        chat_session.save(update_fields=['user'])

    return chat_session


def _store_message(request, role, content):
    """
    모든 사용자의 채팅 메시지를 세션에만 적재합니다.
    """
    history = request.session.get('chat_history', [])
    history.append({'role': role, 'content': content})
    request.session['chat_history'] = history
    request.session.modified = True
    logger.info("[chat] store_message role=%s, history_len=%s, session_key=%s", role, len(history), request.session.session_key)


def _store_summary_entry(request, summary_text: str):
    """
    LangGraph에서 만들어준 요약만 ChatMessage DB에 저장합니다.
    """
    if not summary_text:
        logger.info("[chat] summary empty, skip DB persist.")
        return

    chat_session = _get_or_create_session_for_user(request)
    if chat_session is None:
        logger.warning("[chat] cannot persist summary: chat_session missing.")
        return

    logger.info(
        "[chat] storing summary (len=%s) for session %s",
        len(summary_text),
        chat_session.id or "anonymous",
    )
    ChatMessage.objects.update_or_create(
        session=chat_session,
        role=ChatMessage.Role.SYSTEM,
        defaults={'content': summary_text},
    )
    chat_session.save(update_fields=['updated_at'])
    request.session['chat_memory_summary'] = summary_text
    request.session.modified = True


class ChatView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """채팅 히스토리 조회."""
        _hydrate_summary_from_db(request)
        chat_history = request.session.get("chat_history", [])
        active_session = _get_or_create_session_for_user(request, create=False)
        return Response(
            {
                "chat_history": chat_history,
                "active_session_id": active_session.id if active_session else None,
            }
        )

    def post(self, request):
        """LangGraph 호출."""
        error = None
        ai_response = ""

        _hydrate_summary_from_db(request)
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"error": "query is required"}, status=400)

        try:
            logger.info("[chat] POST question='%s'", query)
            _store_message(request, ChatMessage.Role.USER, query)
            question_for_ai = query

            memory_summary = request.session.get("chat_memory_summary")
            if not memory_summary:
                memory_summary = _hydrate_summary_from_db(request)

            logger.info(
                "[chat] memory_summary len=%s",
                len(memory_summary) if memory_summary else 0,
            )

            app = create_graph_flow()
            response_state = asyncio.run(
                app.ainvoke(
                    {
                        "query": question_for_ai,
                        "tag": "chat",
                    }
                )
            )
            ai_response = response_state.get("final_answer", "")
            logger.info("[chat] AI response len=%s", len(ai_response))

            _store_message(
                request,
                ChatMessage.Role.ASSISTANT,
                ai_response,
            )

            new_summary = response_state.get("summary")
            if new_summary:
                _store_summary_entry(request, new_summary)
        except Exception:
            logger.exception("[chat] langgraph failed")
            error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        chat_history = request.session.get("chat_history", [])
        active_session = _get_or_create_session_for_user(request, create=False)
        return Response(
            {
                "chat_history": chat_history,
                "error": error,
                "active_session_id": active_session.id if active_session else None,
                "answer": ai_response,
            }
        )


class ChatbotHealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class DeleteActiveChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        chat_session = _get_or_create_session_for_user(request, create=False)
        if chat_session and chat_session.user_id == request.user.id:
            ChatMessage.objects.filter(session=chat_session).delete()
            chat_session.delete()
        request.session.pop("chat_history", None)
        request.session.pop("chat_memory_summary", None)
        request.session.modified = True
        return Response({"deleted": True})


def _hydrate_summary_from_db(request):
    """
    세션에 요약이 없고 DB에 저장된 상담 요약이 있다면 불러와서 세션에 복원합니다.
    현재 브라우저 세션 키에 해당하는 ChatSession만 대상으로 합니다.
    """
    cached = request.session.get('chat_memory_summary')
    if cached:
        logger.info("[chat] cached summary found len=%s for session_key=%s", len(cached), request.session.session_key)
        return cached

    if not request.session.session_key:
        request.session.save()

    chat_session = ChatSession.objects.filter(
        session_key=request.session.session_key
    ).first()
    if not chat_session:
        logger.info(
            "[chat] no chat_session found for key=%s",
            request.session.session_key,
        )
        return None

    summaries = list(
        ChatMessage.objects.filter(
            session=chat_session,
            role=ChatMessage.Role.SYSTEM,
        )
        .order_by('-id')
        .values_list('content', flat=True)[:1]
    )
    last_summary = summaries[0] if summaries else None
    if last_summary:
        logger.info(
            "[chat] hydrate summary (session_id=%s, key=%s, len=%s)",
            chat_session.id,
            chat_session.session_key,
            len(last_summary),
        )
        request.session['chat_memory_summary'] = last_summary
        request.session.modified = True
        return last_summary
    logger.info(
        "[chat] no summary rows for session_id=%s key=%s",
        chat_session.id,
        chat_session.session_key,
    )
    return None
