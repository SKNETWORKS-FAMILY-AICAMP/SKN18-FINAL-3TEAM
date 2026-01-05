import React, { useState, useEffect, useRef } from "react";
import { COLORS } from "../../../constants/theme";

/**
 * Claude 스타일의 단계별 접힘이 가능한 AI 사고 과정 시각화 컴포넌트
 * - 각 단계가 개별 박스로 표시
 * - 단계가 끝나면 해당 단계만 자동으로 접힘
 * - 현재 진행 중인 단계는 펼쳐져서 표시
 */

// 단계 그룹 정의 (관련 이벤트들을 그룹화)
const STAGE_GROUPS = {
  question_analysis: {
    title: "질문 분석",
    icon: "🔍",
    events: [
      "history_check_started",
      "history_check_completed",
      "history_check_error",
      "question_analysis_started",
      "question_type_classified",
      "keywords_extracted",
      "stage1_completed",
    ],
    color: "#3B82F6",
  },
  intent_clarification: {
    title: "의도 확인",
    icon: "💭",
    events: [
      "direction_generation_started",
      "direction_generation_completed",
      "intent_options_generated",
      "user_selection_completed",
      "user_selection_processing",
      "intent_integration",
    ],
    color: "#8B5CF6",
  },
  entity_expansion: {
    title: "키워드 확장 및 인물/사건 추출",
    icon: "🧩",
    events: [
      "entity_expansion_started",
      "keyword_expansion_started",
      "keyword_expansion_completed",
      "ttl_matching_started",
      "ttl_matching_completed",
      "pgvector_search_started",
      "pgvector_search_completed",
      "sparql_scoring_started",
      "entity_expansion_completed",
    ],
    color: "#10B981",
  },
  semantic_expansion: {
    title: "의미론적 확장",
    icon: "🌐",
    events: [
      "semantic_expansion_started",
      "temporal_expansion_completed",
      "causal_expansion_completed",
      "pgvector_expansion_completed",
    ],
    color: "#F59E0B",
  },
  knowledge_retrieval: {
    title: "지식 검색",
    icon: "🔎",
    events: ["thread_weights_applied", "sparql_search_completed"],
    color: "#EC4899",
  },
  answer_generation: {
    title: "답변 생성",
    icon: "✍️",
    events: ["answer_generation_started"],
    color: "#06B6D4",
  },
};

// 이벤트를 스테이지 그룹으로 매핑
const getStageGroup = (eventType) => {
  for (const [groupId, group] of Object.entries(STAGE_GROUPS)) {
    if (group.events.includes(eventType)) {
      return { groupId, ...group };
    }
  }
  return {
    groupId: "other",
    title: "기타 처리",
    icon: "📋",
    color: COLORS.gray,
  };
};

// 개별 단계 컴포넌트
const ThinkingStep = ({ stage, events, isActive, isComplete, onToggle }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const contentRef = useRef(null);

  // 완료되면 자동으로 접기
  useEffect(() => {
    if (isComplete && !isActive) {
      const timer = setTimeout(() => {
        setIsExpanded(false);
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [isComplete, isActive]);

  // 활성화되면 펼치기
  useEffect(() => {
    if (isActive) {
      setIsExpanded(true);
    }
  }, [isActive]);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
    if (onToggle) onToggle();
  };

  return (
    <div
      style={{
        marginBottom: "12px",
        border: `1px solid ${isActive ? stage.color : "#e5e7eb"}`,
        borderRadius: "12px",
        overflow: "hidden",
        backgroundColor: COLORS.white,
        boxShadow: isActive
          ? `0 2px 12px ${stage.color}20`
          : "0 1px 3px rgba(0, 0, 0, 0.05)",
        transition: "all 0.3s ease",
      }}
    >
      {/* 헤더 */}
      <div
        style={{
          padding: "12px 16px",
          backgroundColor: isActive ? `${stage.color}10` : "#f9fafb",
          borderBottom: isExpanded
            ? `1px solid ${isActive ? stage.color : "#e5e7eb"}`
            : "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          transition: "background-color 0.2s",
        }}
        onClick={toggleExpand}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* 상태 인디케이터 */}
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "50%",
              backgroundColor: isComplete
                ? `${stage.color}20`
                : isActive
                ? stage.color
                : "#e5e7eb",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "14px",
              transition: "all 0.3s",
            }}
          >
            {isComplete ? (
              <span style={{ color: stage.color }}>✓</span>
            ) : isActive ? (
              <div
                style={{
                  width: "10px",
                  height: "10px",
                  border: `2px solid white`,
                  borderTop: `2px solid transparent`,
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
            ) : (
              <span style={{ fontSize: "12px" }}>{stage.icon}</span>
            )}
          </div>

          <span
            style={{
              fontSize: "14px",
              fontWeight: "600",
              color: isActive ? stage.color : COLORS.dark,
            }}
          >
            {stage.title}
          </span>

          {isActive && !isComplete && (
            <span
              style={{
                fontSize: "11px",
                color: stage.color,
                backgroundColor: `${stage.color}15`,
                padding: "2px 8px",
                borderRadius: "10px",
                fontWeight: "500",
              }}
            >
              진행 중...
            </span>
          )}

          {isComplete && (
            <span
              style={{
                fontSize: "11px",
                color: "#10B981",
                backgroundColor: "#10B98115",
                padding: "2px 8px",
                borderRadius: "10px",
                fontWeight: "500",
              }}
            >
              완료
            </span>
          )}
        </div>

        <div
          style={{
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s",
            fontSize: "12px",
            color: COLORS.gray,
          }}
        >
          ▼
        </div>
      </div>

      {/* 내용 */}
      <div
        ref={contentRef}
        style={{
          maxHeight: isExpanded ? "500px" : "0",
          overflow: "hidden",
          transition: "max-height 0.3s ease-out",
        }}
      >
        <div style={{ padding: "12px 16px" }}>
          {events.map((event, index) => (
            <EventItem key={index} event={event} stageColor={stage.color} />
          ))}
        </div>
      </div>

      {/* 진행 바 */}
      {isActive && !isComplete && (
        <div
          style={{
            height: "2px",
            backgroundColor: "#f0f0f0",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              backgroundColor: stage.color,
              width: "30%",
              animation: "progress 1.5s ease-in-out infinite",
            }}
          />
        </div>
      )}
    </div>
  );
};

// 개별 이벤트 아이템
const EventItem = ({ event, stageColor }) => {
  const { event: eventType, data } = event;

  const getEventDescription = () => {
    switch (eventType) {
      case "history_check_started":
        return "역사 관련 질문인지 확인 중...";
      case "history_check_completed":
        return data.is_historical ? `역사 질문 확인됨` : "역사 질문이 아님";
      case "history_check_error":
        return "역사 관련 체크 오류 (안전하게 역사 질문으로 처리)";
      case "stage1_completed":
        return "질문 분석 완료 - 사용자 선택 대기";
      case "question_analysis_started":
        return `질문 분석 시작: "${data.query?.slice(0, 30)}..."`;
      case "question_type_classified":
        return `질문 유형: ${data.query_type}`;
      case "keywords_extracted":
        return `키워드 ${data.keywords?.length || 0}개 추출: ${data.keywords
          ?.slice(0, 5)
          .join(", ")}...`;
      case "direction_generation_started":
        return "확장 방향 생성 중...";
      case "direction_generation_completed":
        return `${data.direction_count || 0}개 확장 방향 생성됨`;
      case "user_selection_completed":
        return `✓ 사용자 선택: "${
          data.selected_direction_title || "선택된 방향"
        }" - ${data.action || "상세 분석 진행"}`;
      case "keyword_expansion_started":
        const dirTitle = data.direction_title || "역사적 맥락";
        const propGroups = data.property_groups || [];
        const propInfo =
          propGroups.length > 0 ? ` (${propGroups.join(", ")} 관련)` : "";
        return `키워드 확장 중: "${dirTitle}" 방향${propInfo}`;
      case "keyword_expansion_completed":
        return `키워드 확장 완료: ${data.total_keywords || 0}개 생성됨`;
      case "entity_expansion_started":
        const selectedDir = data.selected_direction;
        const basicKws = data.basic_keywords?.slice(0, 3).join(", ") || "";
        return selectedDir
          ? `선택한 방향: "${selectedDir.title || selectedDir}"`
          : `관련 인물/사건 추출 시작`;
      case "entity_expansion_completed":
        return `총 ${data.total_entities || 0}개 인물/사건 추출 완료`;
      case "ttl_matching_started":
        return "역사 데이터베이스에서 정확 매칭 검색 중...";
      case "ttl_matching_completed":
        return `데이터베이스 매칭: ${
          data.matched_entities || data.matched_count || 0
        }개 발견`;
      case "pgvector_search_started":
        return "유사한 역사 정보 검색 중...";
      case "pgvector_search_completed":
        return `유사 정보 검색: ${
          data.added_entities || data.results_count || 0
        }개 발견`;
      case "semantic_expansion_started":
        return `${data.entity_count || 0}개 항목의 연관 관계 탐색 중...`;
      case "temporal_expansion_completed":
        return `시간적 관계 (before/after/contemporary): ${
          data.results_count || 0
        }개 발견`;
      case "causal_expansion_completed":
        return `인과 관계 (cause/result): ${data.results_count || 0}개 발견`;
      case "pgvector_expansion_completed":
        return `의미적 유사 관계 (벡터 기반): ${
          data.results_count || 0
        }개 발견`;
      case "thread_weights_applied":
        const queryType = data.query_type || "default";
        return `검색 가중치 적용: ${queryType}`;
      case "sparql_search_completed":
        const total = data.total_results || 0;
        const threadResults = data.thread_results || {};
        // 쓰레드 이름 한글 매핑
        const threadNameMap = {
          outgoing_relations: "나가는 관계",
          incoming_relations: "들어오는 관계",
          entity_properties: "엔티티 속성",
          connected_entities: "연결 엔티티",
          type_and_summary: "타입/요약",
        };
        const threadBreakdown = Object.entries(threadResults)
          .map(([thread, count]) => {
            const threadName = threadNameMap[thread] || thread;
            return `${threadName}: ${count}개`;
          })
          .join(", ");
        return `SPARQL 검색 완료: 총 ${total}개 경로\n(${threadBreakdown})`;
      case "answer_generation_started":
        return `${data.evidence_count || 0}개 근거로 답변 생성 중...`;
      default:
        return data.title || eventType;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "10px",
        marginBottom: "8px",
        fontSize: "13px",
        color: COLORS.dark,
      }}
    >
      <div
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          backgroundColor: stageColor,
          marginTop: "6px",
          flexShrink: 0,
        }}
      />
      <span style={{ whiteSpace: "pre-line" }}>{getEventDescription()}</span>
    </div>
  );
};

// 재질문 구분선 컴포넌트
const ClarificationDivider = () => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "12px",
      margin: "16px 0",
      padding: "12px 16px",
      backgroundColor: "#f0f9ff",
      border: "1px solid #bae6fd",
      borderRadius: "12px",
    }}
  >
    <div
      style={{
        width: "28px",
        height: "28px",
        borderRadius: "50%",
        backgroundColor: "#0ea5e9",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "white",
        fontSize: "16px",
        fontWeight: "600",
      }}
    >
      ✓
    </div>
    <div style={{ flex: 1 }}>
      <div
        style={{
          fontSize: "13px",
          fontWeight: "600",
          color: "#0c4a6e",
          marginBottom: "2px",
        }}
      >
        사용자 선택 완료
      </div>
      <div
        style={{
          fontSize: "11px",
          color: "#0369a1",
        }}
      >
        선택한 방향으로 상세 분석을 진행합니다
      </div>
    </div>
  </div>
);

// 메인 ThinkingMode 컴포넌트
const ThinkingMode = ({
  thinkingEvents = [],
  isComplete = false,
  clarification = null,
  onClarificationChoice = null,
  isSubmitting = false,
}) => {
  const [preStages, setPreStages] = useState([]);
  const [postStages, setPostStages] = useState([]);
  const [hasClarification, setHasClarification] = useState(false);

  // 이벤트를 재질문 전/후 + 단계별로 그룹화
  useEffect(() => {
    // 중복 이벤트 제거 (같은 event 타입이 연속으로 나오면 첫 번째만 유지)
    const deduplicatedEvents = thinkingEvents.reduce((acc, event, index) => {
      // 이전 이벤트와 같은 타입이고 데이터도 거의 같으면 스킵
      if (index > 0) {
        const prevEvent = thinkingEvents[index - 1];
        if (
          prevEvent.event === event.event &&
          prevEvent.stage?.is_pre_clarification ===
            event.stage?.is_pre_clarification
        ) {
          // 같은 이벤트 타입이 연속으로 나오면 중복으로 간주하고 스킵
          return acc;
        }
      }
      acc.push(event);
      return acc;
    }, []);

    // 재질문 전/후 이벤트 분리
    const preEvents = deduplicatedEvents.filter(
      (e) => e.stage?.is_pre_clarification === true
    );
    const postEvents = deduplicatedEvents.filter(
      (e) => e.stage?.is_pre_clarification === false
    );

    // 디버깅: 이벤트 분리 결과 확인
    console.log("[ThinkingMode] Event split:", {
      total: deduplicatedEvents.length,
      preEvents: preEvents.length,
      postEvents: postEvents.length,
      samplePreEvent: preEvents[0],
      samplePostEvent: postEvents[0],
    });

    setHasClarification(preEvents.length > 0 && postEvents.length > 0);

    // 재질문 전 이벤트 그룹화
    const preStageMap = new Map();
    preEvents.forEach((event) => {
      const stageInfo = getStageGroup(event.event);
      const groupId = stageInfo.groupId;

      if (!preStageMap.has(groupId)) {
        preStageMap.set(groupId, {
          id: groupId,
          stage: stageInfo,
          events: [],
          isComplete: false,
        });
      }

      preStageMap.get(groupId).events.push(event);
    });

    const preStageList = Array.from(preStageMap.values());
    preStageList.forEach((stage, index) => {
      stage.isComplete =
        postEvents.length > 0 || index < preStageList.length - 1;
      stage.isActive =
        postEvents.length === 0 &&
        !isComplete &&
        index === preStageList.length - 1;
    });
    setPreStages(preStageList);

    // 재질문 후 이벤트 그룹화
    const postStageMap = new Map();
    postEvents.forEach((event) => {
      const stageInfo = getStageGroup(event.event);
      const groupId = stageInfo.groupId;

      if (!postStageMap.has(groupId)) {
        postStageMap.set(groupId, {
          id: groupId,
          stage: stageInfo,
          events: [],
          isComplete: false,
        });
      }

      postStageMap.get(groupId).events.push(event);
    });

    const postStageList = Array.from(postStageMap.values());
    postStageList.forEach((stage, index) => {
      stage.isComplete = isComplete || index < postStageList.length - 1;
      stage.isActive = !isComplete && index === postStageList.length - 1;
    });
    setPostStages(postStageList);
  }, [thinkingEvents, isComplete]);

  if (thinkingEvents.length === 0) {
    return null;
  }

  const totalStages = preStages.length + postStages.length;

  return (
    <div
      style={{
        marginBottom: "16px",
      }}
    >
      {/* 전체 헤더 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: "12px",
          padding: "8px 12px",
          backgroundColor: "#f8fafc",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
        }}
      >
        <span style={{ fontSize: "16px" }}>🧠</span>
        <span
          style={{
            fontSize: "14px",
            fontWeight: "600",
            color: COLORS.dark,
          }}
        >
          AI 사고 과정
        </span>
        <span
          style={{
            fontSize: "11px",
            color: COLORS.gray,
            backgroundColor: COLORS.white,
            padding: "2px 8px",
            borderRadius: "10px",
            border: "1px solid #e2e8f0",
          }}
        >
          {totalStages}단계
        </span>
        {isComplete && (
          <span
            style={{
              fontSize: "11px",
              color: "#10B981",
              backgroundColor: "#10B98115",
              padding: "2px 8px",
              borderRadius: "10px",
              marginLeft: "auto",
            }}
          >
            ✓ 완료
          </span>
        )}
      </div>

      {/* 재질문 전 단계 */}
      {preStages.length > 0 && (
        <div style={{ marginBottom: "8px" }}>
          {preStages.map((stageData) => (
            <ThinkingStep
              key={stageData.id}
              stage={stageData.stage}
              events={stageData.events}
              isActive={stageData.isActive}
              isComplete={stageData.isComplete}
            />
          ))}
        </div>
      )}

      {/* 선택 카드 (의도 확인 단계 다음에 표시) */}
      {clarification && (
        <div style={{ marginTop: "16px", marginBottom: "16px" }}>
          <div
            style={{
              fontSize: "14px",
              color: COLORS.dark,
              lineHeight: "1.5",
              marginBottom: "16px",
              fontWeight: "500",
            }}
          >
            {clarification.question || "어떤 방향의 정보가 더 궁금하신가요?"}
          </div>
          <div
            className="clarification-cards-scroll"
            style={{
              display: "flex",
              gap: "12px",
              overflowX: "auto",
              overflowY: "hidden",
              paddingBottom: "8px",
              paddingRight: "40px",
              marginRight: "-40px",
              WebkitOverflowScrolling: "touch",
              scrollbarWidth: "thin",
              msOverflowStyle: "auto",
              scrollBehavior: "smooth",
              touchAction: "pan-x",
              scrollSnapType: "x proximity",
              width: "100%",
              maxWidth: "none",
            }}
          >
            {clarification.options?.map((option, idx) => {
              const isDisabled = clarification.isSelected || isSubmitting;
              const isThisSelected =
                clarification.selectedId === option.direction_id;
              return (
                <button
                  key={option.direction_id}
                  onClick={(e) => {
                    if (!isDisabled && onClarificationChoice) {
                      e.currentTarget.style.transform = "scale(0.98)";
                      e.currentTarget.style.borderColor = COLORS.primary;
                      e.currentTarget.style.backgroundColor = COLORS.primary;
                      e.currentTarget.style.color = COLORS.dark;
                      onClarificationChoice(option.direction_id, option.title);
                    }
                  }}
                  disabled={isDisabled}
                  style={{
                    minWidth: "180px",
                    maxWidth: "240px",
                    padding: "16px",
                    backgroundColor: isThisSelected
                      ? COLORS.primary
                      : COLORS.white,
                    border: `2px solid ${
                      isThisSelected ? COLORS.primary : COLORS.border
                    }`,
                    borderRadius: "16px",
                    cursor: isDisabled ? "not-allowed" : "pointer",
                    textAlign: "left",
                    transition: "all 0.2s ease-out",
                    opacity: isDisabled && !isThisSelected ? 0.6 : 1,
                    flexShrink: 0,
                    boxShadow: isDisabled
                      ? "0 1px 3px rgba(0,0,0,0.04)"
                      : "0 2px 8px rgba(0,0,0,0.06)",
                    scrollSnapAlign: "start",
                    marginLeft: idx === 0 ? "12px" : "0px",
                    marginRight:
                      idx === clarification.options.length - 1 ? "32px" : "0px",
                  }}
                  onMouseEnter={(e) => {
                    if (!isDisabled) {
                      e.currentTarget.style.borderColor = COLORS.primary;
                      e.currentTarget.style.backgroundColor = COLORS.tertiary;
                      e.currentTarget.style.transform =
                        "translateY(-3px) scale(1.02)";
                      e.currentTarget.style.boxShadow =
                        "0 8px 25px rgba(0,0,0,0.12)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isDisabled && !isThisSelected) {
                      e.currentTarget.style.borderColor = COLORS.border;
                      e.currentTarget.style.backgroundColor = COLORS.white;
                      e.currentTarget.style.transform =
                        "translateY(0) scale(1)";
                      e.currentTarget.style.boxShadow =
                        "0 2px 8px rgba(0,0,0,0.06)";
                    }
                  }}
                  onTouchStart={(e) => {
                    if (!isDisabled) {
                      e.currentTarget.style.transform = "scale(0.98)";
                    }
                  }}
                  onTouchEnd={(e) => {
                    if (!isDisabled) {
                      e.currentTarget.style.transform =
                        "translateY(0) scale(1)";
                    }
                  }}
                >
                  <div
                    style={{
                      fontSize: "12px",
                      fontWeight: "700",
                      color: COLORS.primary,
                      marginBottom: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span
                      style={{
                        width: "24px",
                        height: "24px",
                        borderRadius: "50%",
                        backgroundColor: COLORS.primary,
                        color: COLORS.dark,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "13px",
                        fontWeight: "700",
                      }}
                    >
                      {idx + 1}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: "15px",
                      fontWeight: "600",
                      color: COLORS.dark,
                      marginBottom: "8px",
                      lineHeight: "1.3",
                    }}
                  >
                    {option.title}
                  </div>
                  <div
                    style={{
                      fontSize: "13px",
                      color: COLORS.gray,
                      lineHeight: "1.5",
                    }}
                  >
                    {option.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 재질문 구분선 */}
      {hasClarification && <ClarificationDivider />}

      {/* 재질문 후 단계 */}
      {postStages.length > 0 && (
        <div>
          {postStages.map((stageData) => (
            <ThinkingStep
              key={stageData.id}
              stage={stageData.stage}
              events={stageData.events}
              isActive={stageData.isActive}
              isComplete={stageData.isComplete}
            />
          ))}
        </div>
      )}

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes progress {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(100%); }
          100% { transform: translateX(300%); }
        }
      `}</style>
    </div>
  );
};

export default ThinkingMode;
