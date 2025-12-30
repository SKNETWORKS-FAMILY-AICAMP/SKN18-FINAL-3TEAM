import asyncio
import logging
import json
import uuid

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
    if query.startswith("__CLARIFICATION__:"):
        parts = query.split(":", 2)  # "__CLARIFICATION__", direction_id, title
        if len(parts) >= 2:
            user_selected_direction = parts[1]
        if len(parts) >= 3:
            user_selected_title = parts[2]

        # 원본 질문을 세션에서 복원
        query = request.session.get("pending_clarification_query", query)
        logger.info("[chat] User selected direction: %s (%s) for query: %s",
                   user_selected_direction, user_selected_title, query)

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

        # Thinking 모드일 때만 ontology LangGraph 호출
        if thinking_mode:
            logger.info("[chat] Using ontology LangGraph (Thinking mode)")
            app = create_ontology_graph()
        else:
            logger.info("[chat] Using standard LangGraph")
            app = create_graph_flow()

        # LangGraph 호출 시 사용자 선택 포함
        invoke_params = {
            "query": question_for_ai,
            "tag": "chat",  # ★ Django API 모드 표시
            "session_id": str(chat_session.id) if chat_session else "",
        }

        # 사용자 선택이 있으면 skip_clarification 활성화
        if user_selected_direction:
            invoke_params["user_selected_direction"] = user_selected_direction
            if user_selected_title:
                invoke_params["user_selected_title"] = user_selected_title
            invoke_params["skip_clarification"] = True  # 이미 선택했으므로 재질문 스킵
            logger.info("[chat] User direction selected: %s (%s), skip_clarification=True", 
                       user_selected_direction, user_selected_title or "no title")
        else:
            # 첫 호출에서는 재질문을 위해 중단할 수 있도록 설정
            invoke_params["skip_clarification"] = False
            logger.info("[chat] First call, skip_clarification=False, expecting clarification")

        # ★ 디버그: invoke_params 로깅
        logger.info("[chat] LangGraph invoke_params: %s", {k: v for k, v in invoke_params.items() if k != 'query'})

        response_state = asyncio.run(app.ainvoke(invoke_params))
        ai_response = response_state.get("final_answer") or fallback_answer
        logger.info("[chat] AI response len=%s", len(ai_response))

        # ★ 노드별 실행 시간 로그 출력
        node_times = response_state.get("node_execution_times", {})
        if node_times:
            total_time = sum(node_times.values())
            logger.info("[chat] 총 실행 시간: %.2f초", total_time)

        # ★ Evidences 정보 추출 (경로 시각화용)
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
                evidences=evidences,  # ★ evidences 포함
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

        # 원본 질문을 세션에 저장 (사용자 선택 시 사용)
        request.session["pending_clarification_query"] = query
        request.session.modified = True

        # ai_response는 비워둠 (재질문만 반환)
        ai_response = ""

    except Exception:
        logger.exception("[chat] langgraph failed")
        error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
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
        "evidences": evidences if 'evidences' in locals() else [],  # ★ evidences 포함 (Thinking 모드일 때만 존재)
    }

    # Thinking 모드에서 재질문이 있는 경우 추가 정보 전달
    # ★ 수정: thinking_mode 조건 제거 - 항상 재질문 데이터 반환
    if needs_clarification and expansion_directions:
        response_data["needs_clarification"] = True
        response_data["clarification_question"] = clarification_question
        response_data["expansion_directions"] = expansion_directions
        logger.info("[chat] ★ Returning clarification to frontend: %d options", len(expansion_directions))
    else:
        # 재질문이 완료되었거나 없으면 세션 정리
        request.session.pop("pending_clarification_query", None)
        request.session.modified = True

    return Response(response_data)


class ChatQuestionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 세션 지정 (없으면 현재 세션 키 기준으로 생성)
        session_id = request.data.get("session_id")
        if session_id:
            chat_session = ChatSession.objects.filter(id=session_id, user=request.user).first()
            if not chat_session:
                return Response({"error": "invalid session"}, status=400)
        else:
            chat_session = _get_or_create_session_for_user(request)

        # 스트리밍 요청 여부 (query string 또는 body)
        stream_flag = (
            str(request.query_params.get("stream", "")).lower() in {"1", "true", "yes"}
            or str(request.data.get("stream", "")).lower() in {"1", "true", "yes"}
        )

        if stream_flag:
            error = None
            ai_response = ""
            fallback_answer = "어,어랏? 그게 뭐야아? 그거 조선말 맞아?"

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
            if query.startswith("__CLARIFICATION__:"):
                parts = query.split(":", 2)
                if len(parts) >= 2:
                    user_selected_direction = parts[1]
                if len(parts) >= 3:
                    user_selected_title = parts[2]
                query = request.session.get("pending_clarification_query", query)

            # 재질문 응답이 아닌 경우에만 사용자 메시지 저장
            if not user_selected_direction:
                _store_message(request, ChatMessage.Role.USER, query, chat_session=chat_session)

            # SSE 형태로 스트리밍 응답 (실제 OpenAI 스트리밍)
            async def sse_stream_async():
                nonlocal error, ai_response
                
                try:
                    logger.info("[chat][stream] POST question='%s' thinking_mode=%s", query, thinking_mode)
                    question_for_ai = query

                    memory_summary = request.session.get("chat_memory_summary")
                    if not memory_summary:
                        memory_summary = _hydrate_summary_from_db(request)

                    # Thinking 모드일 때만 ontology LangGraph 호출
                    if thinking_mode:
                        logger.info("[chat][stream] Using ontology LangGraph (Thinking mode)")
                        app = create_ontology_graph()
                    else:
                        logger.info("[chat][stream] Using standard LangGraph")
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
                    else:
                        invoke_params["skip_clarification"] = False

                    # 스트리밍을 위한 큐 (asyncio.Queue 사용)
                    import asyncio
                    stream_queue = asyncio.Queue()
                    loop = asyncio.get_event_loop()
                    
                    # 스트리밍 콜백 함수 (각 청크를 큐에 저장)
                    def stream_callback(chunk_text: str):
                        """스트리밍 청크를 큐에 저장 (비동기 큐에 추가)"""
                        try:
                            # 동기 함수에서 비동기 큐에 추가
                            if loop.is_running():
                                # 이미 실행 중인 루프가 있으면 call_soon_threadsafe 사용
                                asyncio.run_coroutine_threadsafe(
                                    stream_queue.put(chunk_text), loop
                                )
                            else:
                                # 루프가 실행 중이 아니면 직접 추가
                                loop.call_soon_threadsafe(
                                    stream_queue.put_nowait, chunk_text
                                )
                        except Exception as e:
                            logger.error(f"[chat][stream] Callback error: {e}")
                    
                    # 스트리밍 콜백을 state에 추가
                    invoke_params["stream_callback"] = stream_callback
                    
                    # 비동기로 LangGraph 실행 (별도 태스크)
                    async def run_langgraph():
                        nonlocal ai_response
                        try:
                            async for event in app.astream(invoke_params):
                                # 마지막 상태 처리
                                if "__end__" in event:
                                    final_state = event["__end__"]
                                    ai_response = final_state.get("final_answer", "") or fallback_answer
                                    
                                    # 재질문 데이터 확인
                                    needs_clarification = final_state.get("needs_clarification", False)
                                    expansion_directions = final_state.get("expansion_directions", [])
                                    clarification_question = final_state.get("clarification_question", "")
                                    
                                    if needs_clarification and expansion_directions:
                                        await stream_queue.put(("clarification", clarification_question, expansion_directions))
                                        return
                                    
                                    # 최종 답변 저장
                                    evidences = final_state.get("evidences", [])
                                    _store_message(
                                        request,
                                        ChatMessage.Role.ASSISTANT,
                                        ai_response,
                                        chat_session=chat_session,
                                        evidences=evidences,
                                    )
                                    
                                    new_summary = final_state.get("summary")
                                    if new_summary:
                                        _store_summary_entry(request, new_summary, chat_session=chat_session)
                                    
                                    await stream_queue.put(("final", ai_response))
                        except UserClarificationRequired as e:
                            # 사용자 재질문이 필요한 경우
                            response_state = e.state
                            needs_clarification = response_state.get("needs_clarification", True)
                            expansion_directions = response_state.get("expansion_directions", [])
                            clarification_question = response_state.get("clarification_question", "")
                            
                            # 재질문을 AI 메시지로 저장
                            import json as json_module
                            clarification_metadata = {
                                "type": "clarification",
                                "question": clarification_question,
                                "options": expansion_directions
                            }
                            message_with_metadata = f"__CLARIFICATION_METADATA__:{json_module.dumps(clarification_metadata, ensure_ascii=False)}"
                            _store_message(
                                request,
                                ChatMessage.Role.ASSISTANT,
                                message_with_metadata,
                                chat_session=chat_session,
                            )
                            
                            request.session["pending_clarification_query"] = query
                            request.session.modified = True
                            
                            await stream_queue.put(("clarification", clarification_question, expansion_directions))
                        except Exception as e:
                            logger.exception("[chat][stream] langgraph failed")
                            await stream_queue.put(("error", "오류가 발생했습니다. 잠시 후 다시 시도해주세요."))
                    
                    # LangGraph 실행 태스크 시작
                    langgraph_task = asyncio.create_task(run_langgraph())
                    
                    # 스트리밍 청크 전송
                    while True:
                        try:
                            # 큐에서 항목 가져오기 (타임아웃 0.1초)
                            try:
                                item = await asyncio.wait_for(stream_queue.get(), timeout=0.1)
                                
                                if isinstance(item, tuple):
                                    if item[0] == "clarification":
                                        yield f"data: {json.dumps({'type': 'clarification', 'question': item[1], 'options': item[2]})}\n\n"
                                        break
                                    elif item[0] == "final":
                                        yield f"data: {json.dumps({'type': 'final', 'text': item[1]})}\n\n"
                                        break
                                    elif item[0] == "error":
                                        yield f"data: {json.dumps({'type': 'error', 'text': item[1]})}\n\n"
                                        break
                                else:
                                    # 일반 텍스트 청크
                                    yield f"data: {json.dumps({'type': 'delta', 'text': item})}\n\n"
                            except asyncio.TimeoutError:
                                # 큐가 비어있으면 계속 대기
                                if langgraph_task.done():
                                    # 태스크가 완료되었는데 큐가 비어있으면 종료
                                    break
                                continue
                        except Exception as e:
                            logger.error(f"[chat][stream] Stream error: {e}")
                            break
                    
                    # 태스크 완료 대기
                    await langgraph_task
                            
                except Exception as e:
                    logger.exception("[chat][stream] sse_stream failed")
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
                finally:
                    loop.close()

            return StreamingHttpResponse(
                sse_stream(),
                content_type="text/event-stream",
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

            # ★ evidences 메타데이터 복원
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