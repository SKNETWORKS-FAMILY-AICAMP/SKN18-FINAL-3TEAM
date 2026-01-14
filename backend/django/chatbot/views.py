import asyncio
import logging
import json
import uuid
import time
import threading
import queue

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count

from .models import ChatMessage, ChatSession
from backend.langgraph_structure1.graph import create_graph_flow
from backend.langgraph_fuseki.graph import create_graph_flow as create_ontology_graph
from backend.langgraph_fuseki.nodes.user_intent_clarification_node import UserClarificationRequired

logger = logging.getLogger("chatbot")


def clear_thinking_session(request):
    """
    Thinking 관련 세션 데이터 정리 (통일된 함수)

    재질문 전 이벤트는 유지하고, 재질문 관련 임시 데이터만 정리
    """
    request.session.pop('pending_thinking_events', None)
    request.session.pop("pending_clarification_query", None)
    request.session.pop("pending_expansion_directions", None)
    request.session.pop("pending_basic_keywords", None)
    request.session.modified = True
    logger.info("[chat] Thinking session cleared")

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


def _store_message(request, role, content, chat_session=None, evidences=None):
    """
    모든 사용자의 채팅 메시지를 세션에만 적재합니다.
    evidences가 제공되면 함께 저장합니다.
    """
    history = request.session.get('chat_history', [])
    msg_data = {'role': role, 'content': content}

    # evidences가 있으면 함께 저장
    if evidences is not None and role == 'assistant':
        msg_data['evidences'] = evidences

    history.append(msg_data)
    request.session['chat_history'] = history
    request.session.modified = True
    logger.info("[chat] store_message role=%s, history_len=%s, session_key=%s", role, len(history), request.session.session_key)

    # 스트리밍 형태로 frontend에 전달되는 경우
    if chat_session is None:
        chat_session = _get_or_create_session_for_user(request)
        if not chat_session:
            logger.warning("[chat] cannot persist message: chat_session missing.")
            return

    # DB에 저장할 때 evidences를 JSON으로 인코딩하여 content에 포함
    db_content = content
    if evidences is not None and role == 'assistant':
        import json
        # evidences를 메타데이터로 저장
        metadata = {
            "content": content,
            "evidences": evidences
        }
        db_content = f"__EVIDENCE_METADATA__:{json.dumps(metadata, ensure_ascii=False)}"

    ChatMessage.objects.create(
        session=chat_session,
        role=role,
        content=db_content,
    )
    chat_session.save(update_fields=['updated_at'])


def _store_summary_entry(request, summary_text: str, chat_session=None):
    """
    LangGraph에서 만들어준 요약만 ChatMessage DB에 저장합니다.
    """
    if not summary_text:
        logger.info("[chat] summary empty, skip DB persist.")
        return

    if chat_session is None:
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


def _build_session_payload(session: ChatSession):
    first_message = (
        ChatMessage.objects.filter(session=session, role=ChatMessage.Role.USER)
        .order_by("created_at")
        .values_list("content", flat=True)
        .first()
    )
    return {
        "id": session.id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "first_message": first_message,
        "title": (first_message or "대화")[:40],
    }


def _handle_question(request, chat_session=None):
    """LangGraph 호출."""
    error = None
    ai_response = ""
    fallback_answer = "어,어랏? 그게 뭐야아? 그거 조선말 맞아?"
    
    # ========== 재질문 관련 변수 초기화 (수정됨) ==========
    needs_clarification = False
    expansion_directions = []
    clarification_question = ""

    _hydrate_summary_from_db(request)
    query = (request.data.get("query") or request.data.get("question") or "").strip()
    if not query:
        return Response({"error": "query is required"}, status=400)

    # Thinking mode 파라미터 확인
    thinking_mode = request.data.get("thinking_mode", False)

    # 사용자 선택 확인 (재질문에 대한 응답)
    user_selected_direction = None
    user_selected_title = None
    pending_expansion_directions = []  # 세션에서 복원할 확장 방향
    pending_basic_keywords = []  # 세션에서 복원할 기본 키워드
    
    if query.startswith("__CLARIFICATION__:"):
        parts = query.split(":", 2)  # "__CLARIFICATION__", direction_id, title
        if len(parts) >= 2:
            user_selected_direction = parts[1]
        if len(parts) >= 3:
            user_selected_title = parts[2]

        # 세션 키 확인 (디버깅용)
        logger.info("[chat][session] Session key: %s", request.session.session_key)
        logger.info("[chat][session] Session keys available: %s", list(request.session.keys()))

        # 원본 질문 및 확장 방향을 세션에서 복원
        query = request.session.get("pending_clarification_query", query)
        pending_expansion_directions = request.session.get("pending_expansion_directions", [])
        pending_basic_keywords = request.session.get("pending_basic_keywords", [])
        
        logger.info("[chat] User selected direction: %s (%s) for query: %s",
                   user_selected_direction, user_selected_title, query)
        logger.info("[chat] Restored expansion_directions: %d, basic_keywords: %d",
                   len(pending_expansion_directions), len(pending_basic_keywords))
        logger.info("[chat] Restored basic_keywords content: %s", pending_basic_keywords)

        # 사용자가 선택한 옵션을 사용자 메시지로 저장
        if user_selected_title:
            _store_message(request, ChatMessage.Role.USER, user_selected_title, chat_session=chat_session)

    try:
        logger.info("[chat] POST question='%s' thinking_mode=%s", query, thinking_mode)

        # 재질문 응답이 아닌 경우에만 사용자 메시지 저장
        if not user_selected_direction:
            _store_message(request, ChatMessage.Role.USER, query, chat_session=chat_session)

        question_for_ai = query

        memory_summary = request.session.get("chat_memory_summary")
        if not memory_summary:
            memory_summary = _hydrate_summary_from_db(request)

        logger.info(
            "[chat] memory_summary len=%s",
            len(memory_summary) if memory_summary else 0,
        )

        # LangGraph 호출 시 사용자 선택 포함 (먼저 정의)
        invoke_params = {
            "query": question_for_ai,
            "tag": "chat",  # Django API 모드 표시
            "session_id": str(chat_session.id) if chat_session else "",
        }

        # Thinking 모드일 때만 ontology LangGraph 호출
        if thinking_mode:
            logger.info("[chat] Using ontology LangGraph (Thinking mode)")
            app = create_ontology_graph()
            
            # Thinking 콜백 설정 (비스트리밍 모드)
            def thinking_callback(event_dict: dict):
                """
                비스트리밍 모드에서 thinking 이벤트를 세션에 저장
                통일된 이벤트 구조 사용
                """
                if 'pending_thinking_events' not in request.session:
                    request.session['pending_thinking_events'] = []
                request.session['pending_thinking_events'].append(event_dict)
                request.session.modified = True

            invoke_params["thinking_callback"] = thinking_callback
        else:
            logger.info("[chat] Using standard LangGraph")
            app = create_graph_flow()

        # 사용자 선택이 있으면 skip_clarification 활성화
        if user_selected_direction:
            invoke_params["user_selected_direction"] = user_selected_direction
            if user_selected_title:
                invoke_params["user_selected_title"] = user_selected_title
            invoke_params["skip_clarification"] = True  # 이미 선택했으므로 재질문 스킵
            
            # 세션에서 복원한 expansion_directions와 basic_keywords 전달
            if pending_expansion_directions:
                invoke_params["expansion_directions"] = pending_expansion_directions
            if pending_basic_keywords:
                invoke_params["basic_keywords"] = pending_basic_keywords
            
            logger.info("[chat] User direction selected: %s (%s), skip_clarification=True", 
                       user_selected_direction, user_selected_title or "no title")
            logger.info("[chat] invoke_params에 전달: basic_keywords=%d개, expansion_directions=%d개",
                       len(pending_basic_keywords), len(pending_expansion_directions))
            logger.info("[chat] basic_keywords 내용: %s", pending_basic_keywords)
        else:
            # 첫 호출에서는 재질문을 위해 중단할 수 있도록 설정
            invoke_params["skip_clarification"] = False
            logger.info("[chat] First call, skip_clarification=False, expecting clarification")

        response_state = asyncio.run(app.ainvoke(invoke_params))
        ai_response = response_state.get("final_answer") or fallback_answer
        logger.info("[chat] AI response len=%s", len(ai_response))

        # 노드별 실행 시간 로그 출력
        node_times = response_state.get("node_execution_times", {})
        if node_times:
            total_time = sum(node_times.values())
            logger.info("[chat] 총 실행 시간: %.2f초", total_time)

        # Evidences 정보 추출 (경로 시각화용)
        evidences = response_state.get("evidences", [])
        logger.info("[chat] Evidences count=%s", len(evidences))

        # 재질문 데이터 추출
        needs_clarification = response_state.get("needs_clarification", False)
        expansion_directions = response_state.get("expansion_directions", [])
        clarification_question = response_state.get("clarification_question", "")

        # 재질문이 필요한 경우 AI 응답을 저장하지 않음 (사용자 선택 대기)
        if not needs_clarification:
            _store_message(
                request,
                ChatMessage.Role.ASSISTANT,
                ai_response,
                chat_session=chat_session,
                evidences=evidences,  # evidences 포함
            )

            new_summary = response_state.get("summary")
            if new_summary:
                    _store_summary_entry(request, new_summary, chat_session=chat_session)

    except UserClarificationRequired as e:
        # 사용자 재질문이 필요한 경우 (LangGraph가 중단됨)
        logger.info("[chat] User clarification required, returning options to frontend")

        # 예외에 포함된 state에서 재질문 데이터 추출
        response_state = e.state
        needs_clarification = response_state.get("needs_clarification", True)
        expansion_directions = response_state.get("expansion_directions", [])
        clarification_question = response_state.get("clarification_question", "")
        basic_keywords = response_state.get("basic_keywords", [])  # 기본 키워드도 추출

        # 재질문을 AI 메시지로 저장 (대화 기록에 포함)
        # JSON 메타데이터를 메시지 앞에 추가 (프론트엔드 복원용)
        import json
        clarification_metadata = {
            "type": "clarification",
            "question": clarification_question,
            "options": expansion_directions
        }
        message_with_metadata = f"__CLARIFICATION_METADATA__:{json.dumps(clarification_metadata, ensure_ascii=False)}"
        _store_message(
            request,
            ChatMessage.Role.ASSISTANT,
            message_with_metadata,
            chat_session=chat_session,
        )

        # 원본 질문과 확장 방향을 세션에 저장 (사용자 선택 시 복원용)
        request.session["pending_clarification_query"] = query
        request.session["pending_expansion_directions"] = expansion_directions
        request.session["pending_basic_keywords"] = basic_keywords
        request.session.modified = True
        # 중요: 명시적으로 세션 저장
        request.session.save()
        
        logger.info("[chat] Saved to session: expansion_directions=%d, basic_keywords=%d",
                   len(expansion_directions), len(basic_keywords))
        logger.info("[chat] basic_keywords content: %s", basic_keywords)

        # ai_response는 비워둠 (재질문만 반환)
        ai_response = ""

    except Exception:
        logger.exception("[chat] langgraph failed")
        error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        # 에러 발생 시 세션 정리
        clear_thinking_session(request)
        # 일반 오류 시에도 변수 초기화
        needs_clarification = False
        expansion_directions = []
        clarification_question = ""

    chat_history = request.session.get("chat_history", [])
    active_session = _get_or_create_session_for_user(request, create=False)

    response_data = {
        "chat_history": chat_history,
        "error": error,
        "active_session_id": active_session.id if active_session else None,
        "answer": ai_response,
        "evidences": evidences if 'evidences' in locals() else [],  # evidences 포함 (Thinking 모드일 때만 존재)
    }

    # Thinking 모드에서 재질문이 있는 경우 추가 정보 전달
    # 수정: thinking_mode 조건 제거 - 항상 재질문 데이터 반환
    if needs_clarification and expansion_directions:
        response_data["needs_clarification"] = True
        response_data["clarification_question"] = clarification_question
        response_data["expansion_directions"] = expansion_directions
        logger.info("[chat] Returning clarification to frontend: %d options", len(expansion_directions))
    else:
        # 재질문이 완료되었거나 없으면 세션 정리
        if not (needs_clarification and expansion_directions):
            clear_thinking_session(request)

    return Response(response_data)


class ChatQuestionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 변수 초기화 (try 블록 밖에서)
        chat_session = None
        stream_flag = False
        
        try:
            # 세션 지정 (없으면 현재 세션 키 기준으로 생성)
            session_id = request.data.get("session_id")
            if session_id:
                chat_session = ChatSession.objects.filter(id=session_id, user=request.user).first()
                if not chat_session:
                    return Response({"error": "invalid session"}, status=400)
            else:
                chat_session = _get_or_create_session_for_user(request)
        except Exception as e:
            logger.error(f"[ChatQuestionView] Error in initial processing: {str(e)}", exc_info=True)
            return Response({"error": f"Server error: {str(e)}"}, status=500)

        # 스트리밍 요청 여부 (query string 또는 body)
        stream_flag = (
            str(request.query_params.get("stream", "")).lower() in {"1", "true", "yes"}
            or str(request.data.get("stream", "")).lower() in {"1", "true", "yes"}
        )

        if stream_flag:
            error = None
            ai_response = ""
            fallback_answer = "죄송합니다. 답변을 생성하지 못했습니다. 다시 시도해주세요."

            _hydrate_summary_from_db(request)
            query = (
                request.data.get("query")
                or request.data.get("question")
                or ""
            ).strip()
            if not query:
                return Response({"error": "query is required"}, status=400)

            # Thinking mode 파라미터 확인
            thinking_mode = request.data.get("thinking_mode", False)

            # 사용자 선택 확인 (재질문에 대한 응답)
            user_selected_direction = None
            user_selected_title = None
            pending_expansion_directions = []  # 세션에서 복원할 확장 방향
            pending_basic_keywords = []  # 세션에서 복원할 기본 키워드
            
            if query.startswith("__CLARIFICATION__:"):
                parts = query.split(":", 2)  # "__CLARIFICATION__", direction_id, title
                if len(parts) >= 2:
                    user_selected_direction = parts[1]
                if len(parts) >= 3:
                    user_selected_title = parts[2]

                # 원본 질문 및 확장 방향을 세션에서 복원
                query = request.session.get("pending_clarification_query", query)
                pending_expansion_directions = request.session.get("pending_expansion_directions", [])
                pending_basic_keywords = request.session.get("pending_basic_keywords", [])

                # 사용자가 선택한 옵션을 사용자 메시지로 저장
                if user_selected_title:
                    _store_message(request, ChatMessage.Role.USER, user_selected_title, chat_session=chat_session)
            
            # 재질문 응답이 아닌 경우에만 사용자 메시지 저장 (동기 방식)
            if not user_selected_direction:
                _store_message(request, ChatMessage.Role.USER, query, chat_session=chat_session)

            # SSE 형태로 스트리밍 응답 (실제 OpenAI 스트리밍)
            async def sse_stream_async():
                nonlocal error, ai_response
                
                try:
                    question_for_ai = query

                    # 비동기 컨텍스트에서 DB 접근을 위해 sync_to_async 사용
                    from asgiref.sync import sync_to_async
                    
                    # 동기 함수를 비동기로 래핑
                    async_hydrate_summary = sync_to_async(_hydrate_summary_from_db, thread_sensitive=True)
                    async_store_message = sync_to_async(_store_message, thread_sensitive=True)
                    async_store_summary = sync_to_async(_store_summary_entry, thread_sensitive=True)
                    
                    memory_summary = request.session.get("chat_memory_summary")
                    if not memory_summary:
                        memory_summary = await async_hydrate_summary(request)

                    # Thinking 모드일 때만 ontology LangGraph 호출
                    if thinking_mode:
                        app = create_ontology_graph()
                    else:
                        app = create_graph_flow()

                    # LangGraph 호출 시 사용자 선택 포함
                    invoke_params = {
                        "query": question_for_ai,
                        "tag": "chat",
                        "session_id": str(chat_session.id) if chat_session else "",
                        "stream_mode": True,  # 스트리밍 모드 활성화
                    }

                    # 사용자 선택이 있으면 skip_clarification 활성화
                    if user_selected_direction:
                        invoke_params["user_selected_direction"] = user_selected_direction
                        if user_selected_title:
                            invoke_params["user_selected_title"] = user_selected_title
                        invoke_params["skip_clarification"] = True
                        
                        # 세션에서 복원한 expansion_directions와 basic_keywords 전달
                        if pending_expansion_directions:
                            invoke_params["expansion_directions"] = pending_expansion_directions
                        if pending_basic_keywords:
                            invoke_params["basic_keywords"] = pending_basic_keywords
                        
                    else:
                        invoke_params["skip_clarification"] = False

                    # 스트리밍을 위한 큐 (asyncio.Queue 사용)
                    import asyncio
                    stream_queue = asyncio.Queue()
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.get_event_loop()
                    
                    # 🧠 이전 thinking 이벤트들을 스트리밍 큐에 먼저 전송 (재질문 응답인 경우에만)
                    if user_selected_direction:
                        pending_events = request.session.get('pending_thinking_events', [])
                        if pending_events:
                            for event in pending_events:
                                await stream_queue.put(event)
                            # 복원 후 세션에서 제거
                            request.session.pop('pending_thinking_events', None)
                            request.session.modified = True

                        # 🎯 사용자 선택 완료 이벤트 전송
                        user_selection_event = {
                            "event": "user_selection_completed",
                            "title": "사용자 선택 완료",
                            "stage": {
                                "number": 1,
                                "name": "Stage 1: Query Classifier",
                                "is_pre_clarification": True  # 의도 확인 단계에 포함
                            },
                            "data": {
                                "selected_direction_id": user_selected_direction,
                                "selected_direction_title": user_selected_title or "선택된 방향",
                                "action": "선택한 방향으로 상세 분석 진행"
                            },
                            "timestamp": time.time()
                        }
                        await stream_queue.put(user_selection_event)
                    else:
                        # 새 질문인 경우 이전 thinking 이벤트 제거
                        if 'pending_thinking_events' in request.session:
                            request.session.pop('pending_thinking_events', None)
                            request.session.modified = True
                    
                    # 스트리밍 콜백 함수 (각 청크를 큐에 저장)
                    def stream_callback(chunk_text: str):
                        """스트리밍 청크를 큐에 저장 (비동기 큐에 추가)"""
                        try:
                            # 동기 함수에서 비동기 큐에 추가
                            # LangGraph는 동기 컨텍스트에서 실행되므로 다른 스레드에서 호출될 수 있음
                            if loop.is_running():
                                # 실행 중인 루프가 있으면 run_coroutine_threadsafe 사용
                                future = asyncio.run_coroutine_threadsafe(
                                    stream_queue.put(chunk_text), loop
                                )
                                # 결과를 기다리지 않음 (non-blocking)
                            else:
                                # 루프가 실행 중이 아니면 직접 추가 시도
                                try:
                                    stream_queue.put_nowait(chunk_text)
                                except asyncio.QueueFull:
                                    pass
                        except Exception as e:
                            pass
                    
                    # Thinking 모드 진행 상황 콜백 함수
                    def thinking_callback(event_name: str, event_data: dict):
                        """
                        Thinking 모드 진행 상황을 큐에 저장 + 세션에 저장
                        통일된 이벤트 구조 사용

                        Args:
                            event_name: 이벤트 이름 (예: "history_check_started")
                            event_data: 이벤트 데이터 딕셔너리
                        """
                        try:
                            # is_pre_clarification 자동 설정
                            if "stage" in event_data:
                                # stage가 문자열이면 딕셔너리로 변환
                                if isinstance(event_data["stage"], str):
                                    event_data["stage"] = {
                                        "name": event_data["stage"],
                                        "is_pre_clarification": not user_selected_direction
                                    }
                                # stage가 딕셔너리이고 is_pre_clarification이 없으면 추가
                                elif isinstance(event_data["stage"], dict):
                                    if "is_pre_clarification" not in event_data["stage"]:
                                        event_data["stage"]["is_pre_clarification"] = not user_selected_direction
                            else:
                                # stage 필드가 없으면 생성
                                event_data["stage"] = {
                                    "is_pre_clarification": not user_selected_direction
                                }

                            # data 필드 정리
                            # 이미 data 필드가 있으면 그대로 사용, 없으면 생성
                            if "data" in event_data:
                                data_fields = event_data.get("data", {})
                            else:
                                # data 필드가 없으면 title, stage, timestamp를 제외한 나머지를 data로
                                reserved_fields = {"title", "stage", "event", "timestamp"}
                                data_fields = {}
                                for key, value in list(event_data.items()):
                                    if key not in reserved_fields:
                                        data_fields[key] = value

                            # 이벤트 딕셔너리 구성 (표준 구조)
                            event_dict = {
                                "event": event_name,
                                "title": event_data.get("title", ""),
                                "stage": event_data.get("stage", {}),
                                "data": data_fields,
                                "timestamp": event_data.get("timestamp", time.time())
                            }

                            # 세션에 thinking 이벤트 저장 (재질문 시 복원용)
                            if 'pending_thinking_events' not in request.session:
                                request.session['pending_thinking_events'] = []
                            request.session['pending_thinking_events'].append(event_dict)
                            request.session.modified = True

                            # 즉시 큐에 추가하여 스트리밍 전송
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    stream_queue.put(event_dict), loop
                                )
                            else:
                                try:
                                    stream_queue.put_nowait(event_dict)
                                except asyncio.QueueFull:
                                    pass
                        except Exception as e:
                            pass
                    
                    # 스트리밍 콜백을 state에 추가
                    invoke_params["stream_callback"] = stream_callback
                    if thinking_mode:
                        invoke_params["thinking_callback"] = thinking_callback
                    
                    # 비동기로 LangGraph 실행 (별도 태스크)
                    async def run_langgraph():
                        nonlocal ai_response
                        try:
                            # 비동기 모드로 실행 (hybrid_node가 async def이므로 ainvoke 사용)
                            try:
                                final_state = await app.ainvoke(invoke_params)
                                
                                ai_response = final_state.get("final_answer", "") or fallback_answer
                                
                                # 재질문 데이터 확인
                                needs_clarification = final_state.get("needs_clarification", False)
                                expansion_directions = final_state.get("expansion_directions", [])
                                clarification_question = final_state.get("clarification_question", "")
                                
                                if needs_clarification and expansion_directions:
                                    await stream_queue.put(("clarification", clarification_question, expansion_directions))
                                    return
                                
                                # 최종 답변 저장 (비동기 컨텍스트에서 DB 접근)
                                evidences = final_state.get("evidences", [])
                                
                                await async_store_message(
                                    request,
                                    ChatMessage.Role.ASSISTANT,
                                    ai_response,
                                    chat_session=chat_session,
                                    evidences=evidences,
                                )
                                
                                new_summary = final_state.get("summary")
                                if new_summary:
                                    await async_store_summary(request, new_summary, chat_session=chat_session)
                                
                                await stream_queue.put(("final", ai_response, evidences))

                                # 정상 완료 시 세션 정리
                                async_clear_session = sync_to_async(clear_thinking_session, thread_sensitive=True)
                                await async_clear_session(request)
                                
                            except UserClarificationRequired as e:
                                # 사용자 재질문이 필요한 경우
                                response_state = e.state
                                needs_clarification = response_state.get("needs_clarification", True)
                                expansion_directions = response_state.get("expansion_directions", [])
                                clarification_question = response_state.get("clarification_question", "")
                                basic_keywords = response_state.get("basic_keywords", [])  # 기본 키워드도 추출
                                
                                
                                # 재질문을 AI 메시지로 저장 (비동기 컨텍스트에서 DB 접근)
                                import json as json_module
                                clarification_metadata = {
                                    "type": "clarification",
                                    "question": clarification_question,
                                    "options": expansion_directions
                                }
                                message_with_metadata = f"__CLARIFICATION_METADATA__:{json_module.dumps(clarification_metadata, ensure_ascii=False)}"
                                
                                await async_store_message(
                                    request,
                                    ChatMessage.Role.ASSISTANT,
                                    message_with_metadata,
                                    chat_session=chat_session,
                                )
                                
                                # 원본 질문과 확장 방향을 세션에 저장 (사용자 선택 시 복원용)
                                # 중요: sync_to_async를 사용하여 세션 저장을 명시적으로 수행
                                def save_clarification_to_session():
                                    """동기 컨텍스트에서 세션에 재질문 데이터 저장"""
                                    request.session["pending_clarification_query"] = query
                                    request.session["pending_expansion_directions"] = expansion_directions
                                    request.session["pending_basic_keywords"] = basic_keywords
                                    request.session.modified = True
                                    # 중요: 명시적으로 세션 저장 (스트리밍 응답에서는 미들웨어가 저장하지 않을 수 있음)
                                    request.session.save()
                                
                                async_save_session = sync_to_async(save_clarification_to_session, thread_sensitive=True)
                                await async_save_session()
                                
                                # 🧠 재질문 발생 시 thinking 이벤트는 세션에 보관 (사용자 응답 시 복원)
                                
                                await stream_queue.put(("clarification", clarification_question, expansion_directions))
                                
                        except Exception as e:
                            logger.exception("langgraph failed")
                            # 에러 발생 시 세션 정리
                            async_clear_session = sync_to_async(clear_thinking_session, thread_sensitive=True)
                            await async_clear_session(request)
                            await stream_queue.put(("error", "오류가 발생했습니다. 잠시 후 다시 시도해주세요."))
                    
                    # LangGraph 실행 태스크 시작
                    langgraph_task = asyncio.create_task(run_langgraph())
                    
                    # 스트리밍 청크 전송
                    chunk_sent = 0
                    last_heartbeat_time = time.time()
                    heartbeat_interval = 30  # 30초마다 heartbeat 전송

                    while True:
                        try:
                            # CloudFront timeout 방지를 위한 heartbeat
                            current_time = time.time()
                            if current_time - last_heartbeat_time > heartbeat_interval:
                                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                                last_heartbeat_time = current_time

                            # 큐에서 항목 가져오기 (타임아웃 0.1초)
                            try:
                                item = await asyncio.wait_for(stream_queue.get(), timeout=0.1)

                                if isinstance(item, tuple):
                                    if item[0] == "clarification":
                                        yield f"data: {json.dumps({'type': 'clarification', 'question': item[1], 'options': item[2]})}\n\n"
                                        break
                                    elif item[0] == "final":
                                        # evidences도 함께 전송 (item[2]가 있으면)
                                        evidences_data = item[2] if len(item) > 2 else []
                                        yield f"data: {json.dumps({'type': 'final', 'text': item[1], 'evidences': evidences_data})}\n\n"
                                        break
                                    elif item[0] == "error":
                                        yield f"data: {json.dumps({'type': 'error', 'text': item[1]})}\n\n"
                                        break
                                elif isinstance(item, dict):
                                    # 딕셔너리는 thinking 이벤트 (event 필드 확인)
                                    if "event" in item:
                                        yield f"data: {json.dumps({'type': 'thinking', **item})}\n\n"
                                elif isinstance(item, str):
                                    # 일반 텍스트 청크 (스트리밍)
                                    yield f"data: {json.dumps({'type': 'delta', 'text': item})}\n\n"
                                    chunk_sent += 1
                            except asyncio.TimeoutError:
                                # 큐가 비어있으면 계속 대기
                                if langgraph_task.done():
                                    # 태스크가 완료되었는데 큐가 비어있으면 종료
                                    break
                                continue
                        except Exception as e:
                            break
                    
                    # 태스크 완료 대기
                    await langgraph_task
                            
                except Exception as e:
                    logger.exception("sse_stream failed")
                    error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                    yield f"data: {json.dumps({'type': 'error', 'text': error})}\n\n"
            
            # 동기 제너레이터로 변환
            def sse_stream():
                async_gen = sse_stream_async()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            yield chunk
                        except StopAsyncIteration:
                            break
                        except Exception as e:
                            # 제너레이터 내부 예외 처리
                            logger.exception(f"Generator error: {e}")
                            error_msg = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                            yield f"data: {json.dumps({'type': 'error', 'text': error_msg})}\n\n"
                            break
                except Exception as e:
                    # 최상위 예외 처리
                    logger.exception(f"Stream generator failed: {e}")
                    error_msg = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                    yield f"data: {json.dumps({'type': 'error', 'text': error_msg})}\n\n"
                finally:
                    try:
                        loop.close()
                    except Exception as e:
                        pass

            try:
                return StreamingHttpResponse(
                    sse_stream(),
                    content_type="text/event-stream",
                )
            except Exception as e:
                logger.exception(f"Failed to create StreamingHttpResponse: {e}")
                # 스트리밍 응답 생성 실패 시 일반 에러 응답 반환
                return Response(
                    {"error": "스트리밍 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요."},
                    status=500
                )

        return _handle_question(request, chat_session=chat_session)


class ChatHistoryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = (
            ChatSession.objects.filter(user=request.user)
            .annotate(msg_count=Count("messages"))
            .filter(msg_count__gt=0)
            .order_by("-updated_at")
        )
        return Response({"sessions": [_build_session_payload(session) for session in sessions]})


class ChatSessionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int):
        session = ChatSession.objects.filter(id=session_id, user=request.user).first()
        if session is None:
            return Response({"error": "session not found"}, status=404)

        messages = []
        for msg in ChatMessage.objects.filter(session=session).order_by("created_at"):
            actual_content = msg.content  # DB에서 가져온 원본 content
            evidences = None

            # evidences 메타데이터 복원
            if msg.role == 'assistant' and actual_content.startswith("__EVIDENCE_METADATA__:"):
                try:
                    import json
                    json_str = actual_content[len("__EVIDENCE_METADATA__:"):]
                    metadata = json.loads(json_str)
                    actual_content = metadata.get("content", actual_content)  # 실제 답변 텍스트
                    evidences = metadata.get("evidences", [])
                except Exception as e:
                    logger.error("[chat] Failed to parse evidence metadata: %s", e)

            msg_data = {
                "role": msg.role,
                "content": actual_content,
                "created_at": msg.created_at,
            }

            if evidences is not None:
                msg_data["evidences"] = evidences

            messages.append(msg_data)

        return Response(
            {
                "session": _build_session_payload(session),
                "messages": messages,
            }
        )


class ChatSessionDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id: int):
        session = ChatSession.objects.filter(id=session_id, user=request.user).first()
        if session is None:
            return Response({"error": "session not found"}, status=404)
        ChatMessage.objects.filter(session=session).delete()
        session.delete()
        return Response({"deleted": True})


class NewSessionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 새로운 UUID 기반 세션 키로 생성 (브라우저 session_key 중복 방지)
        session_key = uuid.uuid4().hex
        chat_session = ChatSession.objects.create(
            session_key=session_key,
            user=request.user,
        )
        return Response(_build_session_payload(chat_session), status=201)


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
        return _handle_question(request)


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
