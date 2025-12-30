import React, { useState, useEffect } from 'react';
import { COLORS } from '../../../constants/theme';

/**
 * Claude의 Thinking 모드와 유사한 AI 사고 과정 시각화 컴포넌트
 */
const ThinkingMode = ({ thinkingEvents = [], isComplete = false }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [visibleEvents, setVisibleEvents] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);

  // 이벤트가 추가될 때마다 점진적으로 표시 (더 빠른 애니메이션)
  useEffect(() => {
    if (thinkingEvents.length > visibleEvents.length) {
      const timer = setTimeout(() => {
        setVisibleEvents(thinkingEvents.slice(0, visibleEvents.length + 1));
        setCurrentStep(visibleEvents.length + 1);
      }, 150); // 150ms로 더 빠르게
      return () => clearTimeout(timer);
    }
  }, [thinkingEvents, visibleEvents]);

  // 완료 시 자동으로 접기 (더 빠르게)
  useEffect(() => {
    if (isComplete && thinkingEvents.length > 0) {
      const timer = setTimeout(() => {
        setIsExpanded(false);
      }, 1500); // 1.5초 후 자동으로 접기
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
    if (status === 'completed') return COLORS.success || '#10B981';
    if (status === 'processing') return COLORS.primary;
    if (status === 'error') return COLORS.error || '#EF4444';
    return COLORS.gray;
  };

  const getProgressPercentage = (eventType) => {
    const progressMap = {
      keywords_extracted: 10,
      classification_started: 20,
      intent_options_generated: 30,
      user_selection_processing: 40,
      intent_integration: 50,
      semantic_expansion_started: 60,
      temporal_expansion_completed: 70,
      causal_expansion_completed: 75,
      pgvector_expansion_completed: 80,
      thread_weights_applied: 85,
      sparql_search_completed: 90,
      answer_generation_started: 95
    };
    return progressMap[eventType] || 0;
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
                borderRadius: '4px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                  <span style={{ color: COLORS.primary }}>가중치 매트릭스</span> ({data.query_type})
                </div>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#e3f2fd', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Semantic: {Math.round(data.weight_matrix.semantic_weight * 100)}%
                  </span>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#f3e5f5', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Thread: {Math.round(data.weight_matrix.thread_weight * 100)}%
                  </span>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#e8f5e8', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Entity: {Math.round(data.weight_matrix.entity_boost * 100)}%
                  </span>
                </div>
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
                borderRadius: '4px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                  <span style={{ color: COLORS.primary }}>가중치 매트릭스</span> ({data.query_type})
                </div>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#f3e5f5', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Thread: {Math.round(data.weight_matrix.thread * 100)}%
                  </span>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#e3f2fd', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Semantic: {Math.round(data.weight_matrix.semantic * 100)}%
                  </span>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#e8f5e8', 
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: '500'
                  }}>
                    Boost: {Math.round(data.weight_matrix.entity_boost * 100)}%
                  </span>
                </div>
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
              <div style={{ 
                fontSize: '11px', 
                color: COLORS.gray,
                marginBottom: '4px'
              }}>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {Object.entries(data.thread_results).map(([thread, count]) => (
                    <span key={thread} style={{ 
                      padding: '2px 6px', 
                      backgroundColor: '#e8f4fd', 
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '500'
                    }}>
                      {thread}: {count}개
                    </span>
                  ))}
                </div>
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

  if (thinkingEvents.length === 0) {
    return null;
  }

  const currentProgress = visibleEvents.length > 0 ? 
    getProgressPercentage(visibleEvents[visibleEvents.length - 1]?.event) : 0;

  return (
    <div style={{
      marginBottom: '16px',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '12px',
      overflow: 'hidden',
      backgroundColor: COLORS.white,
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)'
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
          {!isComplete && (
            <span style={{ 
              fontSize: '11px', 
              color: COLORS.primary,
              backgroundColor: 'rgba(255,255,255,0.9)',
              padding: '2px 6px',
              borderRadius: '8px',
              fontWeight: '500'
            }}>
              {currentProgress}%
            </span>
          )}
        </div>
        <div style={{
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
          fontSize: '12px'
        }}>
          ▼
        </div>
      </div>

      {/* 진행률 바 */}
      {!isComplete && (
        <div style={{
          height: '3px',
          backgroundColor: '#f0f0f0',
          position: 'relative'
        }}>
          <div style={{
            height: '100%',
            backgroundColor: COLORS.primary,
            width: `${currentProgress}%`,
            transition: 'width 0.3s ease',
            borderRadius: '0 3px 3px 0'
          }} />
        </div>
      )}

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