import {
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
  lazy,
  Suspense,
} from "react";
import { COLORS } from "../../../constants/theme";

// react-force-graph-2d lazy load
const ForceGraph2D = lazy(() =>
  import("react-force-graph-2d").then((module) => ({
    default: module.default || module.ForceGraph2D || module,
  }))
);

/**
 * Evidence 경로 시각화 컴포넌트
 * 키워드 → 엔티티 → 프로퍼티 연결을 그래프로 표시
 */
const EvidencePathView = ({ evidences = [] }) => {
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [isExpanded, setIsExpanded] = useState(false);
  const [graphError, setGraphError] = useState(null);
  const graphRef = useRef(null);
  const containerRef = useRef(null);

  // 그래프 데이터 생성 - 완전한 키워드 확장 경로 시각화
  const graphData = useMemo(() => {
    if (!evidences || evidences.length === 0) {
      return { nodes: [], links: [] };
    }

    const nodes = [];
    const links = [];
    const nodeMap = new Map();

    // 노드 ID 생성 헬퍼
    const getNodeId = (type, name) => `${type}:${name}`;

    // 노드 추가 헬퍼
    const addNode = (id, name, type, metadata = {}) => {
      if (!nodeMap.has(id)) {
        nodes.push({
          id,
          name,
          type,
          ...metadata,
        });
        nodeMap.set(id, true);
      }
    };

    // 키워드 확장 추적 정보 수집 (실제 evidence 데이터에서 추출)
    const allKeywords = new Set();
    const initialKeywords = new Set();
    const expandedKeywords = new Set();

    // evidence들에서 키워드 정보 수집
    evidences.forEach((evidence) => {
      const trace = evidence.trace;
      if (trace && trace.matched_keyword) {
        allKeywords.add(trace.matched_keyword);

        if (trace.is_from_expansion) {
          expandedKeywords.add(trace.matched_keyword);
        } else {
          initialKeywords.add(trace.matched_keyword);
        }
      }
    });

    // Set을 Array로 변환
    const initialKeywordsArray = Array.from(initialKeywords);
    const expandedKeywordsArray = Array.from(expandedKeywords);

    console.log("키워드 추출 결과:", {
      initialKeywords: initialKeywordsArray,
      expandedKeywords: expandedKeywordsArray,
      totalEvidences: evidences.length,
      sampleEvidence: evidences[0]?.trace,
    });

    // 1. 초기 키워드 노드 추가 (Kiwi 추출)
    initialKeywordsArray.forEach((keyword) => {
      const keywordId = getNodeId("keyword", `initial_${keyword}`);
      addNode(keywordId, keyword, "keyword", {
        isInitial: true,
        keywordType: "initial",
        evidence: {
          description: `Kiwi 형태소 분석기로 추출된 초기 키워드`,
          extractionMethod: "kiwi",
        },
      });
    });

    // 2. 확장된 키워드 노드 추가 (LLM 확장)
    expandedKeywordsArray.forEach((keyword) => {
      if (!initialKeywordsArray.includes(keyword)) {
        const keywordId = getNodeId("keyword", `expanded_${keyword}`);
        addNode(keywordId, keyword, "keyword", {
          isInitial: false,
          keywordType: "expanded",
          evidence: {
            description: `LLM으로 확장된 키워드`,
            extractionMethod: "llm_expansion",
          },
        });
      }
    });

    // 3. 키워드 확장 링크 추가
    if (expandedKeywordsArray.length > 0) {
      // 초기 키워드들을 확장 키워드들과 연결 (개념적 연결)
      initialKeywordsArray.forEach((initialKw) => {
        expandedKeywordsArray.forEach((expandedKw) => {
          if (initialKw !== expandedKw) {
            const initialId = getNodeId("keyword", `initial_${initialKw}`);
            const expandedId = getNodeId("keyword", `expanded_${expandedKw}`);

            links.push({
              source: initialId,
              target: expandedId,
              label: "확장",
              linkType: "keyword_expansion",
              direction: "expansion",
            });
          }
        });
      });
    }

    // 4. 엔티티 및 속성/관계 노드 추가 (기존 로직 + 키워드 연결)
    evidences.forEach((evidence, index) => {
      const trace = evidence.trace;
      if (!trace) return;

      const sourceEntity = trace.source_entity;
      // URI 대신 라벨 사용 - 우선순위: label > name > URI의 마지막 부분
      let entityName = "Unknown";
      if (sourceEntity) {
        // 1순위: label 필드 사용
        if (sourceEntity.label) {
          entityName = sourceEntity.label;
        }
        // 2순위: name이 URI가 아닌 경우 사용
        else if (sourceEntity.name && !sourceEntity.name.includes('_') && !sourceEntity.name.startsWith('http')) {
          entityName = sourceEntity.name;
        }
        // 3순위: URI에서 의미있는 부분 추출
        else if (sourceEntity.name) {
          // URI에서 마지막 부분 추출 (예: "Nation_f4326a53" -> "Nation")
          const uriParts = sourceEntity.name.split('_');
          if (uriParts.length > 1) {
            entityName = uriParts[0]; // 첫 번째 부분 사용
          } else {
            entityName = sourceEntity.name;
          }
        }
      }
      
      const entityType = sourceEntity?.type || "Entity";
      const predicate = trace.predicate_display || trace.predicate || "";
      // predicate도 라벨 형태로 변환
      let predicateLabel = predicate;
      if (predicate && predicate.includes('_')) {
        // "has_nationality" -> "has nationality" 형태로 변환
        predicateLabel = predicate.replace(/_/g, ' ');
      }
      const threadType = trace.thread || "";
      const expansionMethod = trace.expansion_method || "none";

      // 엔티티 노드 추가
      const entityId = getNodeId("entity", entityName);

      // 노드에 evidence 정보 저장 (호버 시 표시용)
      const nodeEvidence = {
        threadType,
        description: evidence.description || "",
        rawData: evidence.raw_data || {},
        summary:
          evidence.raw_data?.summary?.value || evidence.raw_data?.summary || "",
        entityType: entityType,
        year: evidence.raw_data?.year?.value || evidence.raw_data?.year || "",
        category:
          evidence.raw_data?.category?.value ||
          evidence.raw_data?.category ||
          "",
        // 키워드 추적 정보
        matchedKeyword: trace.matched_keyword || "",
        matchMethod: trace.entity_match_type || "",
        expansionMethod: trace.expansion_method || "",
        isFromExpansion: trace.is_from_expansion || false,
        keywordExpansionMethod: trace.keyword_expansion_method || "",
        // 확장 경로 추적
        isInitialKeyword: !trace.is_from_expansion && !!trace.matched_keyword,
        isExpanded:
          trace.is_from_expansion ||
          (!!trace.expansion_method && trace.expansion_method !== "none"),
      };

      addNode(entityId, entityName, "entity", {
        entityType,
        expansionMethod,
        evidenceIndex: index,
        evidence: nodeEvidence,
      });

      // 5. 키워드 → 엔티티 연결 추가
      const matchedKeyword = trace.matched_keyword;
      if (matchedKeyword) {
        let keywordId;
        if (trace.is_from_expansion) {
          // 확장된 키워드에서 추출된 엔티티
          keywordId = getNodeId("keyword", `expanded_${matchedKeyword}`);
        } else {
          // 초기 키워드에서 추출된 엔티티
          keywordId = getNodeId("keyword", `initial_${matchedKeyword}`);
        }

        // 키워드 노드가 존재하는지 확인 후 링크 추가
        if (nodeMap.has(keywordId)) {
          links.push({
            source: keywordId,
            target: entityId,
            label: "추출",
            linkType: "entity_extraction",
            direction: "extraction",
            extractionMethod: trace.is_from_expansion ? "expanded" : "initial",
          });
        }
      }

      // 6. 프로퍼티/관계 노드 추가 (라벨 우선 사용)
      const description = evidence.description || "";
      let targetName = "";

      // description에서 타겟 추출
      if (description.includes("→")) {
        const parts = description.split("→");
        if (threadType === "incoming_relations" && parts.length > 0) {
          targetName = parts[0].trim();
        } else if (parts.length > 2) {
          targetName = parts[2].trim();
        }
      } else if (description.includes(":")) {
        const parts = description.split(":");
        if (parts.length > 1) {
          targetName = parts[1].trim().substring(0, 50);
        }
      }

      // URI 형태의 targetName을 라벨로 변환
      if (targetName) {
        // URI 패턴 감지 및 변환
        if (targetName.includes('_') && targetName.match(/^[A-Za-z]+_[a-f0-9]+$/)) {
          // "Nation_f4326a53" 형태의 URI에서 "Nation" 추출
          const uriParts = targetName.split('_');
          if (uriParts.length > 1) {
            targetName = uriParts[0];
          }
        }
        
        // raw_data에서 더 나은 라벨 찾기
        if (evidence.raw_data) {
          // label, name, title 등의 필드에서 라벨 찾기
          const possibleLabels = [
            evidence.raw_data.label?.value || evidence.raw_data.label,
            evidence.raw_data.name?.value || evidence.raw_data.name,
            evidence.raw_data.title?.value || evidence.raw_data.title,
          ].filter(Boolean);
          
          if (possibleLabels.length > 0) {
            targetName = possibleLabels[0];
          }
        }
      }

      if (targetName) {
        const targetId = getNodeId(
          "value",
          `${entityName}_${predicate}_${index}`
        );
        addNode(targetId, targetName, "value", {
          predicate,
          threadType,
          evidenceIndex: index,
          evidence: {
            threadType,
            description: evidence.description || "",
            predicate: predicate,
            value: targetName,
            rawData: evidence.raw_data || {},
          },
        });

        // 7. 엔티티 → 속성/관계 링크 추가
        let linkSource, linkTarget;
        if (threadType === "incoming_relations") {
          linkSource = targetId;
          linkTarget = entityId;
        } else {
          linkSource = entityId;
          linkTarget = targetId;
        }

        links.push({
          source: linkSource,
          target: linkTarget,
          label: predicate,
          linkType: "property_relation",
          threadType,
          evidenceIndex: index,
          direction:
            threadType === "incoming_relations" ? "incoming" : "outgoing",
        });
      }
    });

    console.log("그래프 데이터 생성 완료:", {
      totalNodes: nodes.length,
      totalLinks: links.length,
      nodesByType: {
        keyword: nodes.filter((n) => n.type === "keyword").length,
        entity: nodes.filter((n) => n.type === "entity").length,
        value: nodes.filter((n) => n.type === "value").length,
      },
      linksByType: {
        keyword_expansion: links.filter(
          (l) => l.linkType === "keyword_expansion"
        ).length,
        entity_extraction: links.filter(
          (l) => l.linkType === "entity_extraction"
        ).length,
        property_relation: links.filter(
          (l) => l.linkType === "property_relation"
        ).length,
      },
    });

    return { nodes, links };
  }, [evidences]);

  // 노드 색상 결정
  const getNodeColor = useCallback(
    (node) => {
      if (selectedNode && selectedNode.id === node.id) {
        return "#ff6b35"; // 선택된 노드
      }

      // 키워드 노드 색상 체계 (노란색 계열)
      if (node.type === "keyword") {
        if (node.isInitial) {
          return "#FEF3C7"; // 초기 키워드: 연한 노란색 (Kiwi 추출)
        } else {
          return "#F59E0B"; // LLM 확장 키워드: 진한 노란색
        }
      }

      if (node.type === "entity") {
        // 지식 확장된 키워드 (Semantic 확장): 하늘색 계열
        if (node.evidence && node.evidence.isExpanded) {
          return "#7DD3FC"; // 하늘색 (지식 확장된 키워드)
        }
        // 탐색한 키워드 (엔티티): 연한 회색
        return "#D1D5DB"; // 연한 회색
      }

      // 속성값: 더 연한 회색
      if (node.type === "value") {
        return "#F3F4F6"; // 더 연한 회색
      }

      return "#F3F4F6";
    },
    [selectedNode]
  );

  // 노드 크기 결정 - 크기 증가
  const getNodeSize = useCallback(
    (node) => {
      if (selectedNode && selectedNode.id === node.id) {
        return 12; // 선택된 노드 크기 증가 (8 → 12)
      }
      if (node.type === "keyword") {
        return 8; // 키워드 노드 크기 증가 (5 → 8)
      }
      return node.type === "entity" ? 10 : 6; // 엔티티와 값 노드 크기 증가
    },
    [selectedNode]
  );

  // 노드 클릭 핸들러
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
  }, []);

  // 노드 호버 핸들러
  const handleNodeHover = useCallback((node, prevNode) => {
    if (node) {
      setHoveredNode(node);
      // 노드 위치 기준으로 툴팁 위치 설정
      if (node.x !== undefined && node.y !== undefined) {
        const graphContainer = document.querySelector("[data-graph-container]");
        if (graphContainer) {
          const rect = graphContainer.getBoundingClientRect();
          setTooltipPosition({
            x: rect.left + node.x,
            y: rect.top + node.y - 50,
          });
        }
      }
    } else {
      setHoveredNode(null);
    }
  }, []);

  // 마우스 이동 시 툴팁 위치 업데이트
  useEffect(() => {
    if (hoveredNode) {
      const handleMouseMove = (e) => {
        setTooltipPosition({ x: e.clientX + 10, y: e.clientY + 10 });
      };
      window.addEventListener("mousemove", handleMouseMove);
      return () => {
        window.removeEventListener("mousemove", handleMouseMove);
      };
    }
  }, [hoveredNode]);

  // 그래프 확장 시 (0,0) 중심으로 이동 (중복 실행 방지)
  useEffect(() => {
    if (isExpanded && graphRef.current && graphData.nodes.length > 0) {
      const timer = setTimeout(() => {
        if (graphRef.current && !graphRef.current._userCentered) {
          graphRef.current._userCentered = true; // 중복 실행 방지
          try {
            // (0,0) 중심으로 이동
            graphRef.current.centerAt(0, 0, 500);
            
            setTimeout(() => {
              if (graphRef.current) {
                graphRef.current.zoomToFit(400, 50);
              }
            }, 600);
          } catch (error) {
            console.error("[EvidencePathView] center error:", error);
          }
        }
      }, 800); // 시뮬레이션이 어느 정도 안정된 후

      return () => clearTimeout(timer);
    }
  }, [isExpanded]);

  // 그래프 데이터 변경 시 플래그 리셋
  useEffect(() => {
    if (graphRef.current) {
      graphRef.current._centered = false;
      graphRef.current._userCentered = false;
    }
  }, [graphData]);

  if (!evidences || evidences.length === 0) {
    return null;
  }

  // trace 정보가 있는 evidence만 필터링
  const evidencesWithTrace = evidences.filter((ev) => ev.trace);

  if (evidencesWithTrace.length === 0) {
    return null;
  }

  // 드롭다운이 열릴 때 자동 스크롤 (더 부드럽고 신속하게)
  useEffect(() => {
    if (isExpanded && containerRef.current) {
      // 즉시 스크롤 시작 (딜레이 최소화)
      const timer = setTimeout(() => {
        // 가장 가까운 스크롤 가능한 부모 요소 찾기
        let scrollableParent = containerRef.current?.parentElement;
        while (scrollableParent) {
          const style = window.getComputedStyle(scrollableParent);
          if (
            style.overflowY === "auto" ||
            style.overflowY === "scroll" ||
            scrollableParent === document.body
          ) {
            // 컨테이너의 위치 계산
            const containerRect = containerRef.current?.getBoundingClientRect();
            const parentRect = scrollableParent.getBoundingClientRect();
            if (containerRect && parentRect) {
              const scrollTop =
                scrollableParent.scrollTop +
                containerRect.top -
                parentRect.top -
                0; 
              scrollableParent.scrollTo({
                top: scrollTop,
                behavior: "smooth",
              });
            }
            break;
          }
          scrollableParent = scrollableParent.parentElement;
        }
      }, 30); // 딜레이를 더 단축 (50ms → 30ms)
      return () => clearTimeout(timer);
    }
  }, [isExpanded]);

  return (
    <div
      ref={containerRef}
      style={{
        marginTop: "16px",
        backgroundColor: COLORS.white,
        borderRadius: "12px",
        border: `1px solid ${COLORS.border}`,
        overflow: "hidden",
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        minWidth: 0,
      }}
    >
      {/* 헤더 */}
      <div
        style={{
          padding: "12px 16px",
          backgroundColor: COLORS.tertiary,
          borderBottom: `1px solid ${COLORS.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke={COLORS.dark}
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="3" />
            <circle cx="5" cy="5" r="2" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="19" cy="19" r="2" />
            <line x1="7" y1="6" x2="10" y2="10" />
            <line x1="17" y1="6" x2="14" y2="10" />
            <line x1="7" y1="18" x2="10" y2="14" />
            <line x1="17" y1="18" x2="14" y2="14" />
          </svg>
          <span
            style={{
              fontSize: "14px",
              fontWeight: "600",
              color: COLORS.dark,
            }}
          >
            근거 경로 시각화 ({evidencesWithTrace.length}개)
          </span>
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={COLORS.dark}
          strokeWidth="2"
          style={{
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s",
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {/* 그래프 영역 */}
      {isExpanded && (
        <div
          style={{
            padding: "16px",
            backgroundColor: "#fafafa",
            width: "100%",
            maxWidth: "100%",
            boxSizing: "border-box",
            overflow: "hidden",
            minWidth: 0,
          }}
        >
          {/* 범례 */}
          <div
            style={{
              display: "flex",
              gap: "16px",
              marginBottom: "12px",
              flexWrap: "wrap",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: "#FEF3C7",
                }}
              />
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                초기 키워드 (Kiwi 추출)
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: "#F59E0B",
                }}
              />
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                확장된 키워드 (LLM 확장)
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: "#7DD3FC",
                }}
              />
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                지식 확장된 키워드
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: "#D1D5DB",
                }}
              />
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                탐색한 키워드
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: "#F3F4F6",
                }}
              />
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                속성값
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <svg
                width="24"
                height="12"
                viewBox="0 0 24 12"
                style={{ overflow: "visible" }}
              >
                <line
                  x1="2"
                  y1="6"
                  x2="18"
                  y2="6"
                  stroke="#F59E0B"
                  strokeWidth="2"
                  strokeDasharray="3,3"
                />
                <polygon points="18,6 14,3 14,9" fill="#F59E0B" />
              </svg>
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                키워드 확장
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <svg
                width="24"
                height="12"
                viewBox="0 0 24 12"
                style={{ overflow: "visible" }}
              >
                <line
                  x1="2"
                  y1="6"
                  x2="18"
                  y2="6"
                  stroke="#D1D5DB"
                  strokeWidth="2"
                />
                <polygon points="18,6 14,3 14,9" fill="#D1D5DB" />
              </svg>
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                키워드 추출
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <svg
                width="24"
                height="12"
                viewBox="0 0 24 12"
                style={{ overflow: "visible" }}
              >
                <line
                  x1="2"
                  y1="6"
                  x2="18"
                  y2="6"
                  stroke="#F3F4F6"
                  strokeWidth="1"
                />
              </svg>
              <span style={{ fontSize: "12px", color: COLORS.dark }}>
                속성/관계 (화살표 없음)
              </span>
            </div>
          </div>

          {/* 그래프 */}
          <div
            data-graph-container
            style={{
              width: "100%",
              maxWidth: "100%",
              height: isExpanded ? "350px" : "250px", // 높이 더 감소 (400px → 350px, 기본 250px)
              backgroundColor: COLORS.white,
              borderRadius: "8px",
              border: `1px solid ${COLORS.border}`,
              overflow: "hidden", // overflow를 hidden으로 변경
              position: "relative",
              boxSizing: "border-box",
              minWidth: 0,
              cursor: "grab", // 드래그 가능 커서
              userSelect: "none", // 텍스트 선택 방지
            }}
            onMouseDown={(e) => {
              // 마우스 다운 시 드래그 커서
              e.currentTarget.style.cursor = "grabbing";
            }}
            onMouseUp={(e) => {
              // 마우스 업 시 기본 커서
              e.currentTarget.style.cursor = "grab";
            }}
            onMouseLeave={(e) => {
              // 마우스 벗어날 시 기본 커서
              e.currentTarget.style.cursor = "grab";
            }}
          >
            {/* 줌 컨트롤 버튼 */}
            <div
              style={{
                position: "absolute",
                top: "10px",
                right: "10px",
                zIndex: 1000,
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <button
                onClick={() => {
                  if (graphRef.current) {
                    try {
                      const currentZoom = graphRef.current.zoom();
                      const newZoom = Math.min(currentZoom * 1.5, 5);
                      graphRef.current.zoom(newZoom, 300);
                    } catch (error) {
                      console.error("Zoom in error:", error);
                    }
                  }
                }}
                style={{
                  width: "32px",
                  height: "32px",
                  backgroundColor: COLORS.white,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: "4px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "16px",
                  fontWeight: "bold",
                  color: COLORS.dark,
                  boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                }}
                title="확대"
              >
                +
              </button>
              <button
                onClick={() => {
                  if (graphRef.current) {
                    try {
                      const currentZoom = graphRef.current.zoom();
                      const newZoom = Math.max(currentZoom / 1.5, 0.2);
                      graphRef.current.zoom(newZoom, 300);
                    } catch (error) {
                      console.error("Zoom out error:", error);
                    }
                  }
                }}
                style={{
                  width: "32px",
                  height: "32px",
                  backgroundColor: COLORS.white,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: "4px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "16px",
                  fontWeight: "bold",
                  color: COLORS.dark,
                  boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                }}
                title="축소"
              >
                −
              </button>
              <button
                onClick={() => {
                  if (graphRef.current) {
                    try {
                      // 전체 보기: (0,0) 중심으로 조정
                      graphRef.current.zoomToFit(400, 50);
                      setTimeout(() => {
                        if (graphRef.current) {
                          graphRef.current.centerAt(0, 0, 300);
                        }
                      }, 200);
                    } catch (error) {
                      console.error("Fit to view error:", error);
                    }
                  }
                }}
                style={{
                  width: "32px",
                  height: "32px",
                  backgroundColor: COLORS.white,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: "4px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  color: COLORS.dark,
                  boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                }}
                title="전체 보기"
              >
                ⌂
              </button>
            </div>
            {graphError ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: COLORS.gray,
                  fontSize: "14px",
                  gap: "8px",
                }}
              >
                그래프 렌더링 오류가 발생했습니다.
                <button
                  onClick={() => {
                    setGraphError(null);
                    window.location.reload();
                  }}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: COLORS.primary,
                    color: COLORS.dark,
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  새로고침
                </button>
              </div>
            ) : graphData.nodes.length > 0 ? (
              <Suspense
                fallback={
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "100%",
                      color: COLORS.gray,
                    }}
                  >
                    그래프 로딩 중...
                  </div>
                }
              >
                <ForceGraph2D
                  ref={graphRef}
                  graphData={graphData}
                  width={800} // 컨테이너 너비와 일치
                  height={isExpanded ? 350 : 250} // 컨테이너 높이와 일치
                  nodeLabel="name"
                  nodeColor={getNodeColor}
                  nodeRelSize={getNodeSize}
                  // D3 force 설정 - (0,0) 중심 강력 고정
                  d3Force="charge"
                  d3ForceStrength={-120} // 반발력 적당히
                  d3ForceLinkDistance={55} // 링크 거리 적당히
                  d3ForceLinkStrength={0.6} // 링크 강도 적당히
                  d3ForceCenterStrength={1.0} // 중심 끌림 최대화 (0.7 → 1.0)
                  // 애니메이션 설정 - 빠른 안정화
                  d3AlphaDecay={0.05} // 안정화 속도 빠르게 (0.08 → 0.05)
                  d3VelocityDecay={0.8} // 속도 감쇠 강화 (0.7 → 0.8)
                  warmupTicks={100} // 초기 시뮬레이션 틱 증가 (80 → 100)
                  cooldownTicks={50} // 쿨다운 틱 증가 (30 → 50)
                  // 초기 뷰 설정 - 개선된 줌 및 상호작용
                  zoom={1.0} // 줌 레벨 조정 (1.2 → 1.0)
                  minZoom={0.2} // 최소 줌 확대 (0.3 → 0.2)
                  maxZoom={5} // 최대 줌 확대 (4 → 5)
                  // 노드 초기 위치 설정 - (0,0) 중심으로 배치
                  nodeVal={(node) => {
                    // (0,0) 중심 근처에 배치
                    if (!node.x) node.x = (Math.random() - 0.5) * 80;
                    if (!node.y) node.y = (Math.random() - 0.5) * 80;
                    return 1;
                  }}
                  // 그래프 로드 완료 시 중앙 정렬 (단순화)
                  onRenderFramePost={null}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    try {
                      const label = node.name || "";
                      // 개선된 폰트 크기 계산 - 줌에 따른 적응적 크기 조정
                      const baseFontSize = 12;
                      const minFontSize = 8;
                      const maxFontSize = 16;
                      const fontSize = Math.max(
                        minFontSize, 
                        Math.min(maxFontSize, baseFontSize / Math.max(0.5, globalScale))
                      );
                      ctx.font = `bold ${fontSize}px Sans-Serif`;
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";
                      ctx.fillStyle = getNodeColor(node);

                      // 노드 원 그리기
                      if (node.x !== undefined && node.y !== undefined) {
                        ctx.beginPath();
                        ctx.arc(
                          node.x,
                          node.y,
                          getNodeSize(node),
                          0,
                          2 * Math.PI
                        );
                        ctx.fill();

                        // 키워드 노드 특별 표시
                        if (node.type === "keyword") {
                          // 키워드 노드는 테두리 추가
                          ctx.strokeStyle = node.isInitial
                            ? "#F59E0B"
                            : "#7DD3FC";
                          ctx.lineWidth = 2;
                          ctx.stroke();

                          // 초기 키워드는 작은 별표 추가
                          if (node.isInitial) {
                            ctx.fillStyle = "#F59E0B";
                            ctx.font = `bold ${fontSize * 0.8}px Sans-Serif`;
                            ctx.fillText("★", node.x, node.y);
                          }
                        }
                        // 엔티티 노드 특별 표시
                        else if (node.type === "entity") {
                          // 지식 확장된 엔티티인 경우 표시 (작은 사각형)
                          if (node.evidence && node.evidence.isExpanded) {
                            ctx.fillStyle = "#7DD3FC";
                            ctx.fillRect(
                              node.x + getNodeSize(node) - 3,
                              node.y - getNodeSize(node) - 3,
                              4,
                              4
                            );
                          }
                        }

                        // 라벨 그리기 - 개선된 가독성
                        ctx.fillStyle = COLORS.dark;
                        ctx.font = `bold ${fontSize}px Sans-Serif`;

                        // 라벨 배경 (가독성 향상)
                        const textWidth = ctx.measureText(label).width;
                        const padding = 4;
                        ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
                        ctx.fillRect(
                          node.x - textWidth / 2 - padding,
                          node.y + getNodeSize(node) + fontSize / 2,
                          textWidth + padding * 2,
                          fontSize + padding
                        );

                        // 라벨 텍스트
                        ctx.fillStyle = COLORS.dark;
                        ctx.fillText(
                          label,
                          node.x,
                          node.y + getNodeSize(node) + fontSize + 6 // 노드에서 더 멀리 배치
                        );
                      }
                    } catch (error) {
                      console.error(
                        "[EvidencePathView] Error rendering node:",
                        error
                      );
                    }
                  }}
                  linkLabel="label"
                  linkColor={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return "#F59E0B"; // 키워드 확장: 진한 노란색
                    } else if (link.linkType === "entity_extraction") {
                      return "#D1D5DB"; // 키워드 추출: 연한 회색
                    } else {
                      return "#F3F4F6"; // 속성/관계: 더 연한 회색
                    }
                  }}
                  linkWidth={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return 2; // 키워드 확장 링크는 두껍게
                    } else if (link.linkType === "entity_extraction") {
                      return 2; // 키워드 추출 링크도 두껍게
                    } else {
                      return 1; // 속성/관계 링크는 기본
                    }
                  }}
                  linkDirectionalArrowLength={(link) => {
                    // 속성/관계는 화살표 없음
                    if (link.linkType === "property_relation") {
                      return 0;
                    }
                    return 6;
                  }}
                  linkDirectionalArrowRelPos={1}
                  linkDirectionalArrowColor={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return "#F59E0B";
                    } else if (link.linkType === "entity_extraction") {
                      return "#D1D5DB";
                    } else {
                      return "#F3F4F6";
                    }
                  }}
                  linkDirectionalParticles={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return 3; // 키워드 확장은 더 많은 파티클
                    } else if (link.linkType === "entity_extraction") {
                      return 2; // 엔티티 추출은 중간
                    } else {
                      return 1; // 속성/관계는 기본
                    }
                  }}
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleSpeed={0.003}
                  linkCanvasObject={(link, ctx, globalScale) => {
                    try {
                      // 링크 중간 지점 계산
                      if (
                        !link.source ||
                        !link.target ||
                        link.source.x === undefined ||
                        link.target.x === undefined
                      ) {
                        return;
                      }

                      const midX = (link.source.x + link.target.x) / 2;
                      const midY = (link.source.y + link.target.y) / 2;

                      // 라벨 텍스트
                      const label = link.label || "";
                      if (!label) return;

                      // 개선된 링크 라벨 폰트 크기 계산
                      const baseLinkFontSize = 10;
                      const minLinkFontSize = 6;
                      const maxLinkFontSize = 12;
                      const fontSize = Math.max(
                        minLinkFontSize, 
                        Math.min(maxLinkFontSize, baseLinkFontSize / Math.max(0.5, globalScale))
                      );
                      ctx.font = `${fontSize}px Sans-Serif`;
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";

                      // 링크 타입별 색상 설정
                      let textColor = COLORS.dark;
                      let bgColor = "rgba(255, 255, 255, 0.9)";

                      if (link.linkType === "keyword_expansion") {
                        textColor = COLORS.dark;
                        bgColor = "rgba(245, 158, 11, 0.9)"; // 진한 노란색 배경
                      } else if (link.linkType === "entity_extraction") {
                        textColor = COLORS.dark;
                        bgColor = "rgba(209, 213, 219, 0.9)"; // 연한 회색 배경
                      } else {
                        textColor = COLORS.gray;
                        bgColor = "rgba(243, 244, 246, 0.9)"; // 더 연한 회색 배경
                      }

                      // 배경 박스 그리기 (가독성 향상)
                      const textWidth = ctx.measureText(label).width;
                      const padding = 4 / globalScale;
                      const boxWidth = textWidth + padding * 2;
                      const boxHeight = fontSize + padding * 2;

                      ctx.fillStyle = bgColor;
                      ctx.fillRect(
                        midX - boxWidth / 2,
                        midY - boxHeight / 2,
                        boxWidth,
                        boxHeight
                      );

                      // 텍스트 그리기
                      ctx.fillStyle = textColor;
                      ctx.fillText(label, midX, midY);
                    } catch (error) {
                      console.error(
                        "[EvidencePathView] Error rendering link:",
                        error
                      );
                    }
                  }}
                  linkCanvasObjectMode={() => "after"}
                  onNodeClick={handleNodeClick}
                  onNodeHover={handleNodeHover}
                  onNodeDragEnd={(node) => {
                    // 드래그 종료 시 호버 해제
                    if (!hoveredNode || hoveredNode.id !== node.id) {
                      setHoveredNode(null);
                    }
                  }}
                  onBackgroundClick={() => {
                    setSelectedNode(null);
                    setHoveredNode(null);
                  }}
                  onEngineStop={() => {
                    // 시뮬레이션 완료 후 (0,0) 중심으로 한 번만 이동
                    if (graphRef.current && !graphRef.current._centered) {
                      graphRef.current._centered = true; // 중복 실행 방지
                      try {
                        // (0,0) 중심으로 이동
                        graphRef.current.centerAt(0, 0, 300);
                        
                        // 줌 조정
                        setTimeout(() => {
                          if (graphRef.current) {
                            graphRef.current.zoomToFit(400, 50);
                          }
                        }, 400);
                      } catch (error) {
                        console.error("[EvidencePathView] onEngineStop error:", error);
                      }
                    }
                  }}
                  enableNodeDrag={true}
                  enableZoomInteraction={true}
                  enablePanInteraction={true}
                  // 개선된 상호작용 설정
                  nodePointerAreaPaint={(node, color, ctx) => {
                    // 노드 클릭 영역 확대 (더 쉬운 클릭)
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, getNodeSize(node) + 5, 0, 2 * Math.PI);
                    ctx.fill();
                  }}
                  // 줌 제어 개선
                  onZoom={(transform) => {
                    // 줌 레벨에 따른 추가 처리 (필요시)
                    if (transform && transform.k) {
                      // 극단적인 줌에서 텍스트 숨기기 등의 처리 가능
                    }
                  }}
                  // 마우스 이벤트 활성화
                  onNodeRightClick={(node) => {
                    // 우클릭 시 노드 선택
                    setSelectedNode(node);
                  }}
                />
              </Suspense>
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: COLORS.gray,
                  fontSize: "14px",
                }}
              >
                경로 정보가 없습니다
              </div>
            )}
          </div>

          {/* 호버 툴팁 - 개선된 상세 정보 */}
          {hoveredNode && (
            <div
              style={{
                position: "fixed",
                left: `${Math.min(
                  tooltipPosition.x + 10,
                  window.innerWidth - 400
                )}px`,
                top: `${Math.min(
                  tooltipPosition.y + 10,
                  window.innerHeight - 300
                )}px`,
                backgroundColor: COLORS.white,
                border: `1px solid ${COLORS.border}`,
                borderRadius: "12px",
                padding: "16px",
                maxWidth: "380px",
                minWidth: "280px",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.15)",
                zIndex: 10000,
                pointerEvents: "none",
              }}
            >
              {/* 노드 제목 */}
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: "700",
                  color: COLORS.dark,
                  marginBottom: "12px",
                  borderBottom: `1px solid ${COLORS.border}`,
                  paddingBottom: "8px",
                }}
              >
                {hoveredNode.name}
              </div>

              {/* 키워드 노드 정보 */}
              {hoveredNode.type === "keyword" && (
                <div
                  style={{
                    fontSize: "11px",
                    marginBottom: "8px",
                    padding: "8px",
                    backgroundColor: hoveredNode.isInitial
                      ? COLORS.tertiary
                      : COLORS.secondary,
                    borderRadius: "4px",
                    border: `1px solid ${
                      hoveredNode.isInitial ? COLORS.primary : COLORS.sky
                    }`,
                  }}
                >
                  {hoveredNode.isInitial ? (
                    <>
                      <div
                        style={{
                          color: "#F59E0B",
                          fontWeight: "600",
                          marginBottom: "4px",
                        }}
                      >
                        ⭐ 초기 키워드 (Kiwi 추출)
                      </div>
                      <div style={{ color: COLORS.dark, fontSize: "10px" }}>
                        Kiwi 형태소 분석기로 추출된 명사
                      </div>
                    </>
                  ) : (
                    <>
                      <div
                        style={{
                          color: "#F59E0B",
                          fontWeight: "600",
                          marginBottom: "4px",
                        }}
                      >
                        🔗 확장된 키워드 (LLM 확장)
                      </div>
                      <div style={{ color: COLORS.dark, fontSize: "10px" }}>
                        LLM으로 의미적 확장된 키워드
                      </div>
                    </>
                  )}
                  {hoveredNode.evidence?.description && (
                    <div
                      style={{
                        color: COLORS.gray,
                        fontSize: "10px",
                        marginTop: "4px",
                        fontStyle: "italic",
                      }}
                    >
                      {hoveredNode.evidence.description}
                    </div>
                  )}
                </div>
              )}

              {/* 엔티티 상세 정보 - 개선된 버전 */}
              {hoveredNode.type === "entity" && hoveredNode.evidence && (
                <>
                  {/* 기본 정보 */}
                  <div
                    style={{
                      fontSize: "11px",
                      marginBottom: "12px",
                      padding: "10px",
                      backgroundColor: "#F8FAFC",
                      borderRadius: "6px",
                      border: `1px solid ${COLORS.border}`,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "6px",
                      }}
                    >
                      <span style={{ fontWeight: "600", color: COLORS.dark }}>
                        타입:
                      </span>
                      <span style={{ color: COLORS.gray }}>
                        {hoveredNode.evidence.entityType || "Unknown"}
                      </span>
                    </div>
                    {hoveredNode.evidence.year && (
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "6px",
                        }}
                      >
                        <span style={{ fontWeight: "600", color: COLORS.dark }}>
                          연도:
                        </span>
                        <span style={{ color: COLORS.gray }}>
                          {hoveredNode.evidence.year}
                        </span>
                      </div>
                    )}
                    {hoveredNode.evidence.threadType && (
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ fontWeight: "600", color: COLORS.dark }}>
                          Thread:
                        </span>
                        <span style={{ color: COLORS.gray, fontSize: "10px" }}>
                          {hoveredNode.evidence.threadType}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* 키워드 추적 정보 */}
                  <div
                    style={{
                      fontSize: "11px",
                      marginBottom: "12px",
                      padding: "10px",
                      backgroundColor: hoveredNode.evidence.isExpanded
                        ? "#F0F9FF"
                        : "#FFFBEB",
                      borderRadius: "6px",
                      border: `1px solid ${
                        hoveredNode.evidence.isExpanded ? "#7DD3FC" : "#F59E0B"
                      }`,
                    }}
                  >
                    <div
                      style={{
                        color: hoveredNode.evidence.isExpanded
                          ? "#7DD3FC"
                          : "#F59E0B",
                        fontWeight: "600",
                        marginBottom: "6px",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      {hoveredNode.evidence.isExpanded
                        ? "🔗 지식 확장된 키워드"
                        : "📌 초기 추출 키워드"}
                    </div>

                    {hoveredNode.evidence.matchedKeyword && (
                      <div style={{ marginBottom: "4px" }}>
                        <span style={{ fontWeight: "600", color: COLORS.dark }}>
                          매칭 키워드:{" "}
                        </span>
                        <span style={{ color: COLORS.gray }}>
                          {hoveredNode.evidence.matchedKeyword}
                        </span>
                      </div>
                    )}

                    {hoveredNode.evidence.expansionMethod &&
                      hoveredNode.evidence.expansionMethod !== "none" && (
                        <div style={{ marginBottom: "4px" }}>
                          <span
                            style={{ fontWeight: "600", color: COLORS.dark }}
                          >
                            확장 방법:{" "}
                          </span>
                          <span style={{ color: COLORS.gray }}>
                            {hoveredNode.evidence.expansionMethod}
                          </span>
                        </div>
                      )}

                    {hoveredNode.evidence.matchMethod && (
                      <div>
                        <span style={{ fontWeight: "600", color: COLORS.dark }}>
                          매칭 방법:{" "}
                        </span>
                        <span style={{ color: COLORS.gray, fontSize: "10px" }}>
                          {hoveredNode.evidence.matchMethod}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* 요약 정보 */}
                  {hoveredNode.evidence.summary && (
                    <div
                      style={{
                        fontSize: "11px",
                        padding: "10px",
                        backgroundColor: "#F9FAFB",
                        borderRadius: "6px",
                        border: `1px solid ${COLORS.border}`,
                        lineHeight: "1.4",
                      }}
                    >
                      <div
                        style={{
                          fontWeight: "600",
                          color: COLORS.dark,
                          marginBottom: "4px",
                        }}
                      >
                        요약:
                      </div>
                      <div style={{ color: COLORS.gray }}>
                        {hoveredNode.evidence.summary}
                      </div>
                    </div>
                  )}

                  {/* 설명 정보 */}
                  {hoveredNode.evidence.description &&
                    !hoveredNode.evidence.summary && (
                      <div
                        style={{
                          fontSize: "11px",
                          padding: "10px",
                          backgroundColor: "#F9FAFB",
                          borderRadius: "6px",
                          border: `1px solid ${COLORS.border}`,
                          lineHeight: "1.4",
                        }}
                      >
                        <div
                          style={{
                            fontWeight: "600",
                            color: COLORS.dark,
                            marginBottom: "4px",
                          }}
                        >
                          설명:
                        </div>
                        <div style={{ color: COLORS.gray }}>
                          {hoveredNode.evidence.description}
                        </div>
                      </div>
                    )}
                </>
              )}

              {/* 속성/관계 노드 (value 타입) 정보 표시 */}
              {hoveredNode.type === "value" && hoveredNode.evidence && (
                <div
                  style={{
                    fontSize: "11px",
                    marginTop: "8px",
                    padding: "8px",
                    backgroundColor: COLORS.secondary,
                    borderRadius: "4px",
                    border: `1px solid ${COLORS.sky}`,
                  }}
                >
                  <div
                    style={{
                      color: COLORS.sky,
                      fontWeight: "600",
                      marginBottom: "6px",
                    }}
                  >
                    📋 속성/관계 정보
                  </div>
                  {hoveredNode.evidence.predicate && (
                    <div
                      style={{
                        fontSize: "11px",
                        color: COLORS.dark,
                        marginBottom: "4px",
                      }}
                    >
                      <strong>Predicate:</strong>{" "}
                      {hoveredNode.evidence.predicate}
                    </div>
                  )}
                  {hoveredNode.evidence.threadType && (
                    <div
                      style={{
                        fontSize: "10px",
                        color: COLORS.gray,
                        marginBottom: "4px",
                      }}
                    >
                      <strong>타입:</strong> {hoveredNode.evidence.threadType}
                    </div>
                  )}
                  {hoveredNode.evidence.value && (
                    <div
                      style={{
                        fontSize: "11px",
                        color: COLORS.dark,
                        marginTop: "6px",
                        padding: "6px",
                        backgroundColor: COLORS.white,
                        borderRadius: "4px",
                      }}
                    >
                      <strong>값:</strong> {hoveredNode.evidence.value}
                    </div>
                  )}
                  {hoveredNode.evidence.description && (
                    <div
                      style={{
                        fontSize: "10px",
                        color: COLORS.gray,
                        marginTop: "6px",
                        fontStyle: "italic",
                      }}
                    >
                      {hoveredNode.evidence.description}
                    </div>
                  )}
                </div>
              )}

              {/* 엔티티 노드의 type_and_summary 정보 표시 */}
              {hoveredNode.type === "entity" &&
                hoveredNode.evidence &&
                hoveredNode.evidence.threadType === "type_and_summary" && (
                  <>
                    {hoveredNode.evidence.entityType && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.gray,
                          marginBottom: "4px",
                        }}
                      >
                        <strong>타입:</strong> {hoveredNode.evidence.entityType}
                      </div>
                    )}
                    {hoveredNode.evidence.year && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.gray,
                          marginBottom: "4px",
                        }}
                      >
                        <strong>연도:</strong> {hoveredNode.evidence.year}
                      </div>
                    )}
                    {hoveredNode.evidence.category && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.gray,
                          marginBottom: "4px",
                        }}
                      >
                        <strong>분류:</strong> {hoveredNode.evidence.category}
                      </div>
                    )}
                    {hoveredNode.evidence.summary && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.dark,
                          marginTop: "8px",
                          lineHeight: "1.5",
                        }}
                      >
                        {hoveredNode.evidence.summary}
                      </div>
                    )}
                  </>
                )}

              {/* 엔티티 노드의 entity_properties 정보 표시 */}
              {hoveredNode.type === "entity" &&
                hoveredNode.evidence &&
                hoveredNode.evidence.threadType === "entity_properties" && (
                  <>
                    {hoveredNode.evidence.predicate && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.gray,
                          marginBottom: "4px",
                        }}
                      >
                        <strong>속성:</strong> {hoveredNode.evidence.predicate}
                      </div>
                    )}
                    {hoveredNode.evidence.value && (
                      <div style={{ fontSize: "12px", color: COLORS.dark }}>
                        <strong>값:</strong> {hoveredNode.evidence.value}
                      </div>
                    )}
                  </>
                )}

              {/* 기타 정보 */}
              {hoveredNode.type === "entity" &&
                hoveredNode.evidence &&
                hoveredNode.evidence.description &&
                hoveredNode.evidence.threadType !== "type_and_summary" &&
                hoveredNode.evidence.threadType !== "entity_properties" && (
                  <div
                    style={{
                      fontSize: "12px",
                      color: COLORS.dark,
                      marginTop: "4px",
                    }}
                  >
                    {hoveredNode.evidence.description}
                  </div>
                )}
            </div>
          )}

          {/* 선택된 노드 정보 */}
          {selectedNode && (
            <div
              style={{
                marginTop: "12px",
                padding: "12px",
                backgroundColor: COLORS.white,
                borderRadius: "8px",
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <div
                style={{
                  fontSize: "13px",
                  fontWeight: "600",
                  color: COLORS.dark,
                  marginBottom: "6px",
                }}
              >
                {selectedNode.name}
              </div>
              <div style={{ fontSize: "12px", color: COLORS.gray }}>
                타입:{" "}
                {selectedNode.type === "keyword"
                  ? selectedNode.isInitial
                    ? "초기 키워드"
                    : "확장된 키워드"
                  : selectedNode.type === "entity"
                  ? "탐색한 키워드"
                  : "속성값"}
                {selectedNode.entityType && ` (${selectedNode.entityType})`}
                {selectedNode.predicate && ` - ${selectedNode.predicate}`}
              </div>
              {selectedNode.type === "keyword" && selectedNode.evidence && (
                <div
                  style={{
                    fontSize: "12px",
                    color: COLORS.gray,
                    marginTop: "4px",
                  }}
                >
                  추출 방법:{" "}
                  {selectedNode.evidence.extractionMethod || "알 수 없음"}
                </div>
              )}
              {selectedNode.expansionMethod &&
                selectedNode.expansionMethod !== "none" && (
                  <div
                    style={{
                      fontSize: "12px",
                      color: COLORS.gray,
                      marginTop: "4px",
                    }}
                  >
                    확장 방식: {selectedNode.expansionMethod}
                  </div>
                )}
              {selectedNode.evidence && selectedNode.type !== "keyword" && (
                <div
                  style={{
                    fontSize: "12px",
                    color: COLORS.gray,
                    marginTop: "8px",
                    paddingTop: "8px",
                    borderTop: `1px solid ${COLORS.border}`,
                  }}
                >
                  <div>
                    <strong>Thread 타입:</strong>{" "}
                    {selectedNode.evidence.threadType}
                  </div>
                  {selectedNode.evidence.summary && (
                    <div style={{ marginTop: "4px" }}>
                      {selectedNode.evidence.summary}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EvidencePathView;
