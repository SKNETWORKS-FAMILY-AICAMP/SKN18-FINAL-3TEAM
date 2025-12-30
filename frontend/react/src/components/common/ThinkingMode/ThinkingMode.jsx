import React, { useState, useEffect } from 'react';
import { COLORS } from '../../../constants/theme';

/**
 * Claude의 Thinking 모드와 유사한 AI 사고 과정 시각화 컴포넌트
 */
const ThinkingMode = ({ thinkingEvents = [], isComplete = false }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [visibleEvents, setVisibleEvents] = useState([]);

  // 이벤트가 추가될 때마다 점진적으로 표시
  useEffect(() => {
    if (thinkingEvents.length > visibleEvents.length) {
      const timer = setTimeout(() => {
        setVisibleEvents(thinkingEvents.slice(0, visibleEvents.length + 1));
      }, 300); // 300ms 간격으로 이벤트 표시
      return () => clearTimeout(timer);
    }
  }, [thinkingEvents, visibleEvents]);

  // 완료 시 자동으로 접기
  useEffect(() => {
    if (isComplete && thinkingEvents.length > 0) {
      const timer = setTimeout(() => {
        setIsExpanded(false);
      }, 2000); // 2초 후 자동으로 접기
      return () => clearTimeout(timer);
    }
  }, [isComplete, thinkingEvents.length]);

  if (thinkingEvents.length === 0) {
    return null;
  }

  const getEventIcon = (eventType) => {
    const iconMap = {
      keywords_extracted: '🔍',
      classification_started: '🎯',
      intent_options_generated: '💭',
      user_selection_processing: '⚡',
      intent_integration: '🔗',
      semantic_expansion_started: '🌐',
      temporal_expansion_completed: '⏰',
      causal_expansion_completed: '🔄',
      pgvector_expansion_completed: '🔍',
      thread_weights_applied: '⚖️',
      sparql_search_completed: '🔎',
      answer_generation_started: '✍️'
    };
    return iconMap[eventType] || '📋';
  };

  const getEventColor = (eventType, status) => {
    if (status === 'completed') return COLORS.success;
    if (status === 'processing') return COLORS.primary;
    if (status === 'error') return COLORS.error;
    return COLORS.gray;
  };

  const renderEventContent = (event) => {
    const { event: eventType, data } = event;

    switch (eventType) {
      case 'keywords_extracted':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              <strong>추출된 키워드:</strong> {data.keywords?.slice(0, 8).join(', ')}
              {data.keywords?.length > 8 && ` 외 ${data.keywords.length - 8}개`}
            </div>
            <div style={{ fontSize: '12px', color: COLORS.gray }}>
              질문 유형: {data.query_type}
            </div>
          </div>
        );

      case 'classification_started':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              질문을 <strong>{data.query_type}</strong> 유형으로 분류했습니다.
            </div>
            <div style={{ fontSize: '12px', color: COLORS.gray }}>
              전략: {data.strategies?.join(', ')}
            </div>
          </div>
        );

      case 'intent_options_generated':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              <strong>{data.total_count}개</strong>의 의도 선택지를 생성했습니다.
            </div>
            <div style={{ fontSize: '11px', color: COLORS.gray }}>
              처리 시간: {data.processing_time?.toFixed(2)}초
            </div>
          </div>
        );

      case 'intent_integration':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              선택된 의도: <strong>{data.selected_intent?.title}</strong>
            </div>
            <div style={{ fontSize: '11px', color: COLORS.gray, marginBottom: '8px' }}>
              {data.selected_intent?.description}
            </div>
            {data.expanded_keywords?.length > 0 && (
              <div style={{ fontSize: '11px', color: COLORS.gray }}>
                확장 키워드: {data.expanded_keywords.slice(0, 5).join(', ')}
                {data.expanded_keywords.length > 5 && ` 외 ${data.expanded_keywords.length - 5}개`}
              </div>
            )}
          </div>
        );

      case 'semantic_expansion_started':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              <strong>{data.entity_count}개</strong> 엔티티에 대한 의미론적 확장을 시작합니다.
            </div>
            {data.weight_matrix && (
              <div style={{ 
                fontSize: '11px', 
                color: COLORS.gray, 
                marginBottom: '8px',
                padding: '8px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px'
              }}>
                <div><strong>가중치 매트릭스 ({data.query_type}):</strong></div>
                <div>Thread: {data.weight_matrix.thread_weight} | Semantic: {data.weight_matrix.semantic_weight} | Entity: {data.weight_matrix.entity_boost}</div>
              </div>
            )}
            <div style={{ fontSize: '11px', color: COLORS.gray }}>
              활성화된 방법: {Object.entries(data.expansion_methods || {})
                .filter(([_, method]) => method.enabled)
                .map(([name, method]) => `${name} (${method.description})`)
                .join(', ')}
            </div>
          </div>
        );

      case 'temporal_expansion_completed':
      case 'causal_expansion_completed':
      case 'pgvector_expansion_completed':
        return (
          <div>
            <div style={{ marginBottom: '4px' }}>
              <strong>{data.results_count}개</strong> 결과를 찾았습니다.
            </div>
            <div style={{ fontSize: '11px', color: COLORS.gray }}>
              처리 시간: {data.processing_time?.toFixed(2)}초
            </div>
          </div>
        );

      case 'thread_weights_applied':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              <strong>{data.entity_count}개</strong> 엔티티에 대해 <strong>{data.active_threads?.length}개</strong> Thread로 검색합니다.
            </div>
            {data.weight_matrix && (
              <div style={{ 
                fontSize: '11px', 
                color: COLORS.gray,
                padding: '8px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px'
              }}>
                <div><strong>가중치 매트릭스 ({data.query_type}):</strong></div>
                <div>Thread: {data.weight_matrix.thread} | Semantic: {data.weight_matrix.semantic} | Boost: {data.weight_matrix.entity_boost}</div>
              </div>
            )}
          </div>
        );

      case 'sparql_search_completed':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              SPARQL 검색 완료: <strong>{data.total_results}개</strong> 결과
            </div>
            {data.thread_results && (
              <div style={{ fontSize: '11px', color: COLORS.gray }}>
                {Object.entries(data.thread_results).map(([thread, count]) => 
                  `${thread}: ${count}개`
                ).join(', ')}
              </div>
            )}
            <div style={{ fontSize: '11px', color: COLORS.gray }}>
              처리 시간: {data.processing_time?.toFixed(2)}초
            </div>
          </div>
        );

      case 'answer_generation_started':
        return (
          <div>
            <div style={{ marginBottom: '8px' }}>
              <strong>{data.evidence_count}개</strong> 근거를 바탕으로 답변을 생성합니다.
            </div>
            <div style={{ fontSize: '11px', color: COLORS.gray }}>
              질문 유형: {data.query_type} | 스트리밍: {data.stream_mode ? '활성화' : '비활성화'}
            </div>
          </div>
        );

      default:
        return (
          <div style={{ fontSize: '12px', color: COLORS.gray }}>
            {data.title || '처리 중...'}
          </div>
        );
    }
  };

  return (
    <div style={{
      marginBottom: '16px',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '12px',
      overflow: 'hidden',
      backgroundColor: COLORS.white
    }}>
      {/* 헤더 */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: isComplete ? '#f8f9fa' : '#e3f2fd',
          borderBottom: `1px solid ${COLORS.border}`,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ fontSize: '16px' }}>
            {isComplete ? '🧠' : '⚡'}
          </div>
          <span style={{ 
            fontSize: '14px', 
            fontWeight: '600',
            color: COLORS.dark 
          }}>
            {isComplete ? 'AI 사고 과정 (완료)' : 'AI 사고 과정'}
          </span>
          <span style={{ 
            fontSize: '12px', 
            color: COLORS.gray,
            backgroundColor: 'rgba(255,255,255,0.7)',
            padding: '2px 6px',
            borderRadius: '10px'
          }}>
            {visibleEvents.length}단계
          </span>
        </div>
        <div style={{
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
          fontSize: '12px'
        }}>
          ▼
        </div>
      </div>

      {/* 내용 */}
      {isExpanded && (
        <div style={{ padding: '16px' }}>
          {visibleEvents.map((event, index) => {
            const { event: eventType, data } = event;
            const isLast = index === visibleEvents.length - 1;
            const isProcessing = data.status === 'processing' && !isComplete;

            return (
              <div key={index} style={{ 
                display: 'flex', 
                marginBottom: isLast ? '0' : '16px',
                opacity: isProcessing && !isComplete ? 0.7 : 1,
                transition: 'opacity 0.3s'
              }}>
                {/* 아이콘 */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: getEventColor(eventType, data.status),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '14px',
                  marginRight: '12px',
                  flexShrink: 0
                }}>
                  {getEventIcon(eventType)}
                </div>

                {/* 내용 */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '13px',
                    fontWeight: '600',
                    color: COLORS.dark,
                    marginBottom: '4px'
                  }}>
                    {data.title}
                    {isProcessing && !isComplete && (
                      <span style={{ 
                        marginLeft: '8px',
                        fontSize: '11px',
                        color: COLORS.primary 
                      }}>
                        처리 중...
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '12px', color: COLORS.dark }}>
                    {renderEventContent(event)}
                  </div>
                </div>

                {/* 연결선 */}
                {!isLast && (
                  <div style={{
                    position: 'absolute',
                    left: '31px',
                    top: '32px',
                    width: '2px',
                    height: '16px',
                    backgroundColor: COLORS.border,
                    marginLeft: '16px'
                  }} />
                )}
              </div>
            );
          })}

          {/* 로딩 인디케이터 */}
          {!isComplete && visibleEvents.length > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginTop: '12px',
              padding: '8px',
              backgroundColor: '#f8f9fa',
              borderRadius: '6px',
              fontSize: '12px',
              color: COLORS.gray
            }}>
              <div style={{
                width: '12px',
                height: '12px',
                border: `2px solid ${COLORS.border}`,
                borderTop: `2px solid ${COLORS.primary}`,
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              사고 과정 진행 중...
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ThinkingMode;