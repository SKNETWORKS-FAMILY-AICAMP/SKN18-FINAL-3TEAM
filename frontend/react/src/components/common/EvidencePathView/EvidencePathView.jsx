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

    // 노드 추가 헬퍼 (초기 위치는 나중에 배치 로직에서 설정)
    const addNode = (id, name, type, metadata = {}) => {
      if (!nodeMap.has(id)) {
        nodes.push({
          id,
          name,
          type,
          // 초기 위치는 배치 로직에서 설정됨
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
      const entityName = sourceEntity?.name || "Unknown";
      const entityType = sourceEntity?.type || "Entity";
      const predicate = trace.predicate_display || trace.predicate || "";
      const threadType = trace.thread || "";
      const expansionMethod = trace.expansion_method || "none";

      // 엔티티 노드 추가
      const entityId = getNodeId("entity", entityName);

      // 노드에 evidence 정보 저장 (호버 시 표시용)
      // 노드 출처 구분: initial_keyword, llm_expansion, semantic_expansion
      // trace.keyword_source가 있으면 우선 사용, 없으면 expansion_method로 판단
      let keywordSource = trace.keyword_source;
      if (!keywordSource) {
        // expansion_method가 있으면 semantic_expansion
        if (trace.expansion_method && trace.expansion_method !== "none") {
          keywordSource = "semantic_expansion";
        } else {
          // expansion_method가 없으면 is_from_expansion으로 판단
          keywordSource = trace.is_from_expansion
            ? "llm_expansion"
            : "initial_keyword";
        }
      }
      const isSemanticExpansion = keywordSource === "semantic_expansion";

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
        // 노드 출처 구분
        keywordSource: isSemanticExpansion
          ? "semantic_expansion"
          : keywordSource,
        // 확장 경로 추적
        isInitialKeyword: keywordSource === "initial_keyword",
        isLLMExpansion: keywordSource === "llm_expansion",
        isSemanticExpansion: isSemanticExpansion,
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
          // predicate가 있으면 사용, 없으면 빈 문자열
          const linkLabel = predicate || "";
          links.push({
            source: keywordId,
            target: entityId,
            label: linkLabel,
            linkType: "entity_extraction",
            direction: "extraction",
            extractionMethod: trace.is_from_expansion ? "expanded" : "initial",
          });
        }
      }

      // 6. connected_entities 타입 처리 (BFS 경로)
      if (threadType === "connected_entities") {
        const rawData = evidence.raw_data || {};
        const entity1 =
          trace.entity1 || rawData.label1?.value || rawData.label1 || "";
        const entity2 =
          trace.entity2 || rawData.label2?.value || rawData.label2 || "";
        const convergenceNode =
          trace.convergence_node ||
          rawData.convergence_node?.value ||
          rawData.convergence_node ||
          "";
        const path = trace.path || rawData.path?.value || rawData.path || "";
        const isBFS =
          trace.method === "bidirectional_bfs" ||
          rawData.method?.value === "bidirectional_bfs";

        // entity1과 entity2가 모두 있는 경우
        if (entity1 && entity2) {
          const entity1Id = getNodeId("entity", entity1);
          const entity2Id = getNodeId("entity", entity2);

          // entity1 노드 추가 (탐색한 키워드로 표시)
          if (entity1 !== entityName) {
            addNode(entity1Id, entity1, "entity", {
              entityType: "Entity",
              expansionMethod: "none",
              evidenceIndex: index,
              evidence: {
                threadType: "connected_entities",
                description: evidence.description || "",
                rawData: rawData,
                isExplored: true, // 탐색한 노드 표시
              },
            });
          }

          // entity2 노드 추가 (탐색한 키워드로 표시)
          if (entity2 !== entityName) {
            addNode(entity2Id, entity2, "entity", {
              entityType: "Entity",
              expansionMethod: "none",
              evidenceIndex: index,
              evidence: {
                threadType: "connected_entities",
                description: evidence.description || "",
                rawData: rawData,
                isExplored: true, // 탐색한 노드 표시
              },
            });
          }

          // 수렴 노드 추가 (같은 엔티티면 통합)
          if (convergenceNode) {
            // 백엔드에서 전달된 라벨 우선 사용 (SPARQL로 조회한 실제 라벨)
            let convergenceLabel =
              trace.convergence_node_label ||
              rawData.convergence_node_label?.value ||
              rawData.convergence_node_label;

            // 백엔드에서 전달된 라벨이 없으면 URI에서 추출 시도 (하위 호환성)
            if (!convergenceLabel) {
              // URI에서 라벨 추출
              const uriParts =
                convergenceNode.split("#").pop() ||
                convergenceNode.split("/").pop() ||
                convergenceNode;

              // Place_5fbcb94e 형식인 경우, Place 다음 부분이 실제 라벨일 수 있지만
              // 일반적으로는 SPARQL에서 조회한 라벨을 사용해야 함
              // 여기서는 일단 URI에서 추출 (하위 호환성)
              if (uriParts.includes("_")) {
                // 언더스코어로 분리: Place_5fbcb94e → Place만 추출 (임시)
                // 실제로는 백엔드에서 라벨을 조회해서 전달해야 함
                convergenceLabel = uriParts.split("_")[0];
              } else {
                convergenceLabel = uriParts;
              }
            }

            // 수렴 노드도 같은 라벨의 엔티티와 통합 (중복 노드 방지)
            // 기존: `convergence_${convergenceLabel}` → 변경: convergenceLabel만 사용
            const convergenceId = getNodeId("entity", convergenceLabel);

            // 이미 같은 이름의 노드가 있으면 isConvergence 플래그만 추가
            if (nodeMap.has(convergenceId)) {
              // 기존 노드에 수렴 정보 추가 (노드 배열에서 찾아서 업데이트)
              const existingNode = nodes.find((n) => n.id === convergenceId);
              if (existingNode) {
                existingNode.isConvergence = true;
                if (!existingNode.evidence.connectedEntities) {
                  existingNode.evidence.connectedEntities = [];
                }
                if (
                  !existingNode.evidence.connectedEntities.includes(entity1)
                ) {
                  existingNode.evidence.connectedEntities.push(entity1);
                }
                if (
                  !existingNode.evidence.connectedEntities.includes(entity2)
                ) {
                  existingNode.evidence.connectedEntities.push(entity2);
                }
              }
            } else {
              addNode(convergenceId, convergenceLabel, "entity", {
                entityType: "Convergence",
                expansionMethod: "none",
                evidenceIndex: index,
                isConvergence: true,
                evidence: {
                  threadType: "connected_entities",
                  description: `수렴 노드: ${convergenceLabel}`,
                  rawData: rawData,
                  convergenceNode: convergenceNode,
                  connectedEntities: [entity1, entity2],
                  path: path,
                },
              });
            }

            // BFS 경로에서 predicate 추출
            // predicates 정보가 있으면 사용, 없으면 path에서 추출 시도
            let bfsPredicate = "";
            if (trace.predicates) {
              // predicates 형식: "predicate1 → predicate2 → ..."
              const predicateParts = trace.predicates
                .split("→")
                .map((p) => p.trim());
              // 첫 번째 predicate 사용
              if (predicateParts.length > 0) {
                bfsPredicate = predicateParts[0] || "";
              }
            }
            // predicates가 없으면 path에서 추출 시도 (하위 호환성)
            if (!bfsPredicate && path && path.includes("→")) {
              const pathParts = path.split("→").map((p) => p.trim());
              // path 형식: "Entity1 → Entity2 → Entity3"이므로 predicate는 없을 수 있음
              // 하지만 시도해봄
              if (pathParts.length > 1) {
                // URI가 아닌 부분을 predicate로 간주 (실제로는 작동하지 않을 수 있음)
                const possiblePredicate = pathParts[1];
                // URI 패턴이 아닌 경우에만 사용 (간단한 체크)
                if (
                  !possiblePredicate.includes("_") ||
                  !possiblePredicate.match(/^[A-Z][a-z]+_[a-f0-9]+$/)
                ) {
                  bfsPredicate = possiblePredicate;
                }
              }
            }
            // predicate가 없으면 predicate_display 사용
            if (!bfsPredicate) {
              bfsPredicate = trace.predicate_display || trace.predicate || "";
            }

            // entity1 → 수렴 노드 (화살표)
            // 수렴 노드로 가는 방향을 명확히 표시
            if (entity1 !== entityName) {
              links.push({
                source: entity1Id,
                target: convergenceId,
                label: bfsPredicate || "BFS 경로",
                linkType: "bfs_path",
                direction: "exploration",
                isBFS: true,
                path: path,
                convergenceInfo: {
                  from: entity1,
                  to: convergenceLabel,
                  via: bfsPredicate || "BFS",
                },
              });
            }

            // entity2 → 수렴 노드 (화살표)
            // 수렴 노드로 가는 방향을 명확히 표시
            if (entity2 !== entityName) {
              links.push({
                source: entity2Id,
                target: convergenceId,
                label: bfsPredicate || "BFS 경로",
                linkType: "bfs_path",
                direction: "exploration",
                isBFS: true,
                path: path,
                convergenceInfo: {
                  from: entity2,
                  to: convergenceLabel,
                  via: bfsPredicate || "BFS",
                },
              });
            }

            // 메인 엔티티와 수렴 노드 연결 (메인 엔티티 → 수렴 노드)
            // entity1과 entity2가 모두 수렴 노드로 연결되므로, 메인 엔티티도 수렴 노드로 연결
            // 하지만 메인 엔티티가 entity1 또는 entity2와 같을 수 있으므로 중복 방지
            if (entityName !== entity1 && entityName !== entity2) {
              links.push({
                source: entityId,
                target: convergenceId,
                label: bfsPredicate,
                linkType: "bfs_path",
                direction: "exploration",
                isBFS: true,
                path: path,
                convergenceInfo: {
                  entity1: entity1,
                  entity2: entity2,
                  convergenceNode: convergenceLabel,
                },
              });
            }
          } else {
            // 수렴 노드가 없으면 entity1 ↔ entity2 직접 연결 (화살표)
            if (entity1 !== entityName && entity2 !== entityName) {
              // BFS 경로에서 predicate 추출
              let bfsPredicate = "";
              if (trace.predicates) {
                // predicates 형식: "predicate1 → predicate2 → ..."
                const predicateParts = trace.predicates
                  .split("→")
                  .map((p) => p.trim());
                if (predicateParts.length > 0) {
                  bfsPredicate = predicateParts[0] || "";
                }
              }
              // predicates가 없으면 path에서 추출 시도 (하위 호환성)
              if (!bfsPredicate && path && path.includes("→")) {
                const pathParts = path.split("→").map((p) => p.trim());
                if (pathParts.length > 1) {
                  const possiblePredicate = pathParts[1];
                  // URI 패턴이 아닌 경우에만 사용
                  if (
                    !possiblePredicate.includes("_") ||
                    !possiblePredicate.match(/^[A-Z][a-z]+_[a-f0-9]+$/)
                  ) {
                    bfsPredicate = possiblePredicate;
                  }
                }
              }
              if (!bfsPredicate) {
                bfsPredicate = trace.predicate_display || trace.predicate || "";
              }

              links.push({
                source: entity1Id,
                target: entity2Id,
                label: bfsPredicate,
                linkType: "bfs_path",
                direction: "exploration",
                isBFS: true,
                path: path,
              });
            }
          }
        }
      } else {
        // 7. 프로퍼티/관계 노드 추가 (기존 로직)
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
        } else if (threadType === "entity_properties") {
          // entity_properties 타입의 경우 value 필드에서 추출
          const rawData = evidence.raw_data || {};
          targetName = rawData.value?.value || rawData.value || "";
        }

        if (targetName) {
          // Summary 같은 predicate의 경우 "엔티티명의 Summary" 형식으로 라벨 표시
          // 실제 값은 호버창에서 표시
          let nodeLabel = targetName;
          if (predicate && predicate.toLowerCase().includes("summary")) {
            // Summary는 "엔티티명의 Summary" 형식으로 표시
            nodeLabel = `${entityName}의 ${predicate}`;
          } else if (predicate) {
            // 다른 predicate도 "엔티티명의 Predicate" 형식으로 표시
            nodeLabel = `${entityName}의 ${predicate}`;
          }

          const targetId = getNodeId(
            "value",
            `${entityName}_${predicate}_${index}`
          );
          addNode(targetId, nodeLabel, "value", {
            predicate,
            threadType,
            evidenceIndex: index,
            evidence: {
              threadType,
              description: evidence.description || "",
              predicate: predicate,
              value: targetName, // 실제 값은 evidence에 저장
              entityName: entityName, // 어떤 엔티티의 값인지 저장
              rawData: evidence.raw_data || {},
            },
          });

          // 8. 엔티티 → 속성/관계 링크 추가 (화살표 없음)
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
            hasArrow:
              threadType === "outgoing_relations" ||
              threadType === "incoming_relations", // outgoing/incoming은 화살표 표시
          });
        }
      }
    });

    // 노드 배치 최적화: 중심 노드를 중앙에, 연결된 노드를 주변에, 연결되지 않은 중심 노드를 원형으로
    if (nodes.length > 0) {
      // 1. 각 노드의 연결 수 계산
      const nodeConnections = new Map();
      nodes.forEach((node) => {
        nodeConnections.set(node.id, 0);
      });

      links.forEach((link) => {
        const sourceId =
          typeof link.source === "string" ? link.source : link.source.id;
        const targetId =
          typeof link.target === "string" ? link.target : link.target.id;
        nodeConnections.set(sourceId, (nodeConnections.get(sourceId) || 0) + 1);
        nodeConnections.set(targetId, (nodeConnections.get(targetId) || 0) + 1);
      });

      // 2. 노드를 연결 수로 정렬하여 중심 노드 찾기
      const sortedNodes = [...nodes].sort((a, b) => {
        const aConnections = nodeConnections.get(a.id) || 0;
        const bConnections = nodeConnections.get(b.id) || 0;
        return bConnections - aConnections;
      });

      // 3. 중심 노드와 연결된 노드 그룹 찾기 (BFS)
      const visited = new Set();
      const clusters = [];

      sortedNodes.forEach((startNode) => {
        if (visited.has(startNode.id)) return;

        const cluster = [];
        const queue = [startNode];
        visited.add(startNode.id);

        while (queue.length > 0) {
          const currentNode = queue.shift();
          cluster.push(currentNode);

          // 연결된 노드 찾기
          links.forEach((link) => {
            const sourceId =
              typeof link.source === "string" ? link.source : link.source.id;
            const targetId =
              typeof link.target === "string" ? link.target : link.target.id;

            let connectedNode = null;
            if (sourceId === currentNode.id) {
              connectedNode = nodes.find((n) => n.id === targetId);
            } else if (targetId === currentNode.id) {
              connectedNode = nodes.find((n) => n.id === sourceId);
            }

            if (connectedNode && !visited.has(connectedNode.id)) {
              visited.add(connectedNode.id);
              queue.push(connectedNode);
            }
          });
        }

        clusters.push(cluster);
      });

      // 4. 가장 큰 클러스터의 중심 노드를 중앙에 배치
      clusters.sort((a, b) => b.length - a.length);
      const mainCluster = clusters[0] || [];
      const mainHub = mainCluster[0] || sortedNodes[0];

      if (mainHub) {
        mainHub.x = 0;
        mainHub.y = 0;
        // 고정 위치는 시뮬레이션이 안정화된 후에 설정

        // 5. 메인 클러스터의 연결된 노드들을 중심 노드 주변에 원형으로 배치
        const connectedNodes = mainCluster.slice(1);
        const linkDistance = 200; // 링크 거리
        connectedNodes.forEach((node, index) => {
          const angle = (index / connectedNodes.length) * 2 * Math.PI;
          node.x = Math.cos(angle) * linkDistance;
          node.y = Math.sin(angle) * linkDistance;
        });
      }

      // 6. 연결되지 않은 다른 클러스터들을 큰 원의 둘레에 배치
      const outerRadius = 400; // 외부 원 반경
      const otherClusters = clusters.slice(1);
      if (otherClusters.length > 0) {
        otherClusters.forEach((cluster, clusterIndex) => {
          if (cluster.length === 0) return;

          // 원형으로 균등하게 배치
          const clusterAngle =
            (clusterIndex / otherClusters.length) * 2 * Math.PI;
          const clusterCenterX = Math.cos(clusterAngle) * outerRadius;
          const clusterCenterY = Math.sin(clusterAngle) * outerRadius;

          const hub = cluster[0];
          hub.x = clusterCenterX;
          hub.y = clusterCenterY;

          // 클러스터 내 연결된 노드들을 허브 주변에 배치
          const clusterConnected = cluster.slice(1);
          clusterConnected.forEach((node, nodeIndex) => {
            const nodeAngle =
              (nodeIndex / clusterConnected.length) * 2 * Math.PI;
            const nodeRadius = 150; // 클러스터 내 노드 반경
            node.x = clusterCenterX + Math.cos(nodeAngle) * nodeRadius;
            node.y = clusterCenterY + Math.sin(nodeAngle) * nodeRadius;
          });
        });
      }
    }

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

  // 노드 색상 결정 - 범례 색상과 일치
  const getNodeColor = useCallback((node) => {
    // 키워드 노드 색상 체계
    if (node.type === "keyword") {
      if (node.isInitial) {
        return "#FEF3C7"; // 초기 키워드: 연한 노란색
      } else {
        return "#F59E0B"; // LLM 확장 키워드: 진한 노란색
      }
    }

    if (node.type === "entity") {
      // BFS 수렴 노드: 진한 회색 (탐색된 노드)
      if (node.isConvergence) {
        return "#D1D5DB"; // 진한 회색 (탐색된 노드)
      }
      // 탐색한 노드: 진한 회색
      if (node.evidence && node.evidence.isExplored) {
        return "#D1D5DB"; // 진한 회색
      }
      // 노드 출처에 따른 색상 구분
      if (node.evidence) {
        // 지식 확장된 키워드 (Semantic Expander): 연한 파란색 (범례와 일치)
        if (
          node.evidence.isSemanticExpansion ||
          node.evidence.keywordSource === "semantic_expansion"
        ) {
          return "#7DD3FC"; // 연한 파란색 (지식 확장) - 범례와 일치
        }
        // LLM 확장 키워드: 진한 노란색
        if (
          node.evidence.isLLMExpansion ||
          node.evidence.keywordSource === "llm_expansion"
        ) {
          return "#F59E0B"; // 진한 노란색
        }
        // 초기 키워드: 연한 노란색
        if (
          node.evidence.isInitialKeyword ||
          node.evidence.keywordSource === "initial_keyword"
        ) {
          return "#FEF3C7"; // 연한 노란색
        }
        // 기존 로직 (하위 호환성)
        if (!node.evidence.isFromExpansion) {
          return "#FEF3C7"; // 연한 노란색
        }
        if (node.evidence.isFromExpansion) {
          return "#F59E0B"; // 진한 노란색
        }
      }
      // 기본: 연한 노란
      return "#FEF3C7";
    }

    // 속성값: 연한 회색
    if (node.type === "value") {
      return "#E5E7EB";
    }

    return "#FEF3C7";
  }, []);

  // 노드 크기 결정
  const getNodeSize = useCallback((node) => {
    if (node.type === "keyword") {
      return 10; // 키워드 노드
    }
    if (node.type === "entity") {
      return 12; // 엔티티 노드 (가장 큼)
    }
    return 6; // 속성값 노드 (가장 작음)
  }, []);

  // 노드 클릭 핸들러 제거 (사용하지 않음)

  // 노드 호버 핸들러
  const handleNodeHover = useCallback((node) => {
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

  // 컨테이너 크기 상태 추가
  const [containerSize, setContainerSize] = useState({
    width: 800,
    height: 400,
  });

  // 컨테이너 크기 측정
  useEffect(() => {
    const graphContainer = containerRef.current?.querySelector(
      "[data-graph-container]"
    );
    if (graphContainer) {
      const resizeObserver = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const { width, height } = entry.contentRect;
          setContainerSize({
            width: Math.max(width, 400),
            height: Math.max(height, 300),
          });
        }
      });
      resizeObserver.observe(graphContainer);
      return () => resizeObserver.disconnect();
    }
  }, [isExpanded]);

  // 확장 시 한 번만 중앙 정렬 (초기화 시에만) - 중앙 효과 제거
  const hasCenteredRef = useRef(false);

  // d3 force 직접 설정 (원형 배치 + 적정 거리)
  useEffect(() => {
    if (isExpanded && graphRef.current && graphData.nodes.length > 0) {
      const fg = graphRef.current;

      // d3 force 직접 설정
      try {
        // 링크 거리 설정 (적정 거리)
        fg.d3Force("link")?.distance(80).strength(0.3);

        // 반발력 설정 (원형 배치를 위해 적당히)
        fg.d3Force("charge")?.strength(-400).distanceMax(300);

        // 중심 끌림 (클러스터가 화면 중앙에 모이도록)
        fg.d3Force("center")?.strength(0.1);

        // 시뮬레이션 재시작
        fg.d3ReheatSimulation();
      } catch (e) {
        console.log("d3 force 설정 오류:", e);
      }
    }
  }, [isExpanded, graphData.nodes.length]);

  useEffect(() => {
    if (isExpanded && graphRef.current && graphData.nodes.length > 0) {
      // 창이 펼쳐질 때 시뮬레이션 재시작 및 줌 설정
      const immediateTimer = setTimeout(() => {
        if (graphRef.current) {
          try {
            // 시뮬레이션 재시작 (노드 위치 재계산)
            graphRef.current.d3ReheatSimulation();

            // 시뮬레이션 안정화 후 줌 조정
            setTimeout(() => {
              if (graphRef.current) {
                // 초기 줌을 0.8로 설정하여 전체가 보이도록
                graphRef.current.zoom(0.8, 300);
                // 중앙으로 이동
                graphRef.current.centerAt(0, 0, 300);
              }
            }, 500);

            if (!hasCenteredRef.current) {
              hasCenteredRef.current = true; // 한 번만 실행되도록 플래그 설정
            }
          } catch (error) {
            console.error("[EvidencePathView] simulation/zoom error:", error);
          }
        }
      }, 300); // 시뮬레이션이 안정화될 때까지 대기

      return () => {
        clearTimeout(immediateTimer);
      };
    }

    // isExpanded가 false가 되면 플래그 리셋
    if (!isExpanded) {
      hasCenteredRef.current = false;
    }
  }, [isExpanded, graphData.nodes.length, graphData]);

  // 그래프 데이터가 변경될 때 시뮬레이션 재시작
  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0 && isExpanded) {
      const timer = setTimeout(() => {
        if (graphRef.current) {
          try {
            graphRef.current.d3ReheatSimulation();
          } catch (error) {
            console.error(
              "[EvidencePathView] simulation restart error:",
              error
            );
          }
        }
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [graphData.nodes.length, graphData.links.length, isExpanded]);

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
                0; // 여백 증가 (50px → 150px) - 더 많이 스크롤
              scrollableParent.scrollTo({
                top: scrollTop,
                behavior: "smooth",
              });
            }
            break;
          }
          scrollableParent = scrollableParent.parentElement;
        }
      }, 50); // 딜레이를 50ms로 단축
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
                  border: "1px solid #F59E0B",
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
                  backgroundColor: "#E5E7EB",
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
                  stroke="#000000"
                  strokeWidth="1"
                />
                <polygon points="18,6 14,3 14,9" fill="#000000" />
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
              height: "400px", // 높이 감소 (600px → 400px)
              backgroundColor: COLORS.white,
              borderRadius: "8px",
              border: `1px solid ${COLORS.border}`,
              overflow: "visible", // overflow 변경으로 상호작용 활성화
              position: "relative",
              boxSizing: "border-box",
              minWidth: 0,
              display: "flex", // flex 추가
              alignItems: "center", // 세로 중앙 정렬
              justifyContent: "center", // 가로 중앙 정렬
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
                  width={containerSize.width}
                  height={containerSize.height}
                  nodeLabel="name"
                  nodeColor={getNodeColor}
                  nodeRelSize={getNodeSize}
                  // 노드 간격 조정 및 애니메이션 설정 (원형 배치)
                  d3Force="charge"
                  d3ForceStrength={-400} // 적당한 반발력 (원형 배치)
                  d3ForceLinkDistance={80} // 적당한 링크 거리
                  d3ForceLinkStrength={0.3} // 링크 강도
                  d3ForceCenterStrength={0.1} // 중심 끌림
                  // 애니메이션 설정 - 안정화 후 정지
                  d3AlphaDecay={0.02} // 느린 안정화
                  d3VelocityDecay={0.4} // 속도 감쇠
                  warmupTicks={100} // 초기 시뮬레이션 틱
                  cooldownTicks={200} // 쿨다운 후 정지
                  // 초기 뷰 설정
                  minZoom={0.2}
                  maxZoom={4}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    try {
                      const label = node.name || "";
                      // 폰트 크기를 줄여서 텍스트 겹침 방지
                      const fontSize = Math.max(7, 10 / globalScale);
                      ctx.font = `${fontSize}px Sans-Serif`;
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";
                      // 노드 색상 가져오기 (범례와 일치)
                      const nodeColor = getNodeColor(node);
                      ctx.fillStyle = nodeColor;

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
                          // 초기 키워드와 확장 키워드 모두 주황색 테두리
                          ctx.strokeStyle = "#F59E0B"; // 주황색 테두리
                          ctx.lineWidth = 2;
                          ctx.stroke();

                          // 초기 키워드는 작은 별표 추가 (유지)
                          if (node.isInitial) {
                            ctx.fillStyle = "#F59E0B";
                            ctx.font = `bold ${fontSize * 0.8}px Sans-Serif`;
                            ctx.fillText("★", node.x, node.y);
                          }
                        }
                        // 엔티티 노드 특별 표시
                        else if (node.type === "entity") {
                          // 지식 확장된 엔티티인 경우 표시 (작은 사각형)
                          if (
                            node.evidence &&
                            (node.evidence.isSemanticExpansion ||
                              node.evidence.keywordSource ===
                                "semantic_expansion")
                          ) {
                            ctx.fillStyle = "#7DD3FC";
                            ctx.fillRect(
                              node.x + getNodeSize(node) - 3,
                              node.y - getNodeSize(node) - 3,
                              4,
                              4
                            );
                          }
                        }

                        // 라벨 그리기 - 볼드체로 변경
                        ctx.fillStyle = COLORS.dark;
                        ctx.font = `bold ${fontSize}px Sans-Serif`; // 볼드체 적용

                        // 긴 라벨 잘라내기 (최대 8자) - 모든 노드에 적용
                        const displayLabel =
                          label.length > 8
                            ? label.substring(0, 8) + "..."
                            : label;

                        // 라벨 텍스트 - 볼드체 (배경 없이)
                        ctx.fillStyle = COLORS.dark;
                        ctx.font = `bold ${fontSize}px Sans-Serif`; // 볼드체 재적용
                        ctx.fillText(
                          displayLabel,
                          node.x,
                          node.y + getNodeSize(node) + fontSize / 2 + 4
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
                    } else if (link.linkType === "bfs_path") {
                      return "#9CA3AF"; // BFS 경로: 중간 회색
                    } else {
                      return "#F3F4F6"; // 속성/관계: 더 연한 회색
                    }
                  }}
                  linkWidth={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return 2; // 키워드 확장 링크는 두껍게
                    } else if (link.linkType === "entity_extraction") {
                      return 2; // 키워드 추출 링크도 두껍게
                    } else if (link.linkType === "bfs_path") {
                      return 2; // BFS 경로는 두껍게
                    } else {
                      return 1; // 속성/관계 링크는 기본
                    }
                  }}
                  linkDirectionalArrowLength={(link) => {
                    // 수렴 노드(BFS 경로): 화살표 필수
                    if (link.linkType === "bfs_path") {
                      return 12; // 화살표 크기 증가
                    }
                    // outgoing/incoming 관계: 화살표 필수
                    if (
                      link.linkType === "property_relation" &&
                      (link.threadType === "outgoing_relations" ||
                        link.threadType === "incoming_relations")
                    ) {
                      return 12; // 화살표 크기 증가
                    }
                    // 속성/관계: hasArrow가 false면 화살표 없음, true면 화살표 표시
                    if (link.linkType === "property_relation") {
                      return link.hasArrow ? 12 : 0;
                    }
                    // 키워드 확장, 추출은 화살표 표시
                    return 12; // 화살표 크기 증가
                  }}
                  linkDirectionalArrowRelPos={0.95}
                  linkDirectionalArrowColor={(link) => {
                    if (link.linkType === "keyword_expansion") {
                      return "#F59E0B";
                    } else if (link.linkType === "entity_extraction") {
                      return "#D1D5DB";
                    } else if (link.linkType === "bfs_path") {
                      return "#9CA3AF"; // BFS 경로 화살표 색상
                    } else {
                      return "#F3F4F6";
                    }
                  }}
                  linkDirectionalParticle={0.0}
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

                      // 링크 각도 계산
                      const dx = link.target.x - link.source.x;
                      const dy = link.target.y - link.source.y;
                      const angle = Math.atan2(dy, dx);

                      const midX = (link.source.x + link.target.x) / 2;
                      const midY = (link.source.y + link.target.y) / 2;

                      // 라벨 텍스트
                      const label = link.label || "";
                      if (!label) return;

                      // 작은 폰트 크기
                      const fontSize = Math.max(4, 8 / globalScale);
                      ctx.font = `${fontSize}px Sans-Serif`;
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";

                      // 텍스트 크기 측정
                      const textWidth = ctx.measureText(label).width;
                      const padding = 4 / globalScale;
                      const boxWidth = textWidth + padding * 2;
                      const boxHeight = fontSize + padding * 2;

                      // 선의 수직 방향 계산 (상단부로 이동하기 위해)
                      const perpendicularAngle = angle + Math.PI / 2; // 90도 회전
                      const offsetDistance = 12 / globalScale; // 선 위로 이동할 거리

                      // 상단부 위치 계산 (수직 방향으로 위로 이동)
                      const textX =
                        midX + Math.cos(perpendicularAngle) * offsetDistance;
                      const textY =
                        midY + Math.sin(perpendicularAngle) * offsetDistance;

                      // 회전 적용 (선을 따라 텍스트 배치)
                      ctx.save();
                      ctx.translate(textX, textY);

                      // 텍스트가 거꾸로 보이지 않도록 각도 조정
                      let rotationAngle = angle;
                      if (Math.abs(angle) > Math.PI / 2) {
                        rotationAngle = angle + Math.PI;
                      }
                      ctx.rotate(rotationAngle);

                      // 선 위에 보이도록 흰색 배경 그리기 (최소한의 박스)
                      ctx.fillStyle = "rgba(255, 255, 255, 0.9)"; // 반투명 흰색 배경
                      ctx.fillRect(
                        -boxWidth / 2,
                        -boxHeight / 2,
                        boxWidth,
                        boxHeight
                      );

                      // 텍스트 그리기
                      ctx.fillStyle = "#000000"; // 검은색 텍스트
                      ctx.fillText(label, 0, 0);

                      ctx.restore();
                    } catch (error) {
                      console.error(
                        "[EvidencePathView] Error rendering link:",
                        error
                      );
                    }
                  }}
                  linkCanvasObjectMode={() => "after"}
                  onNodeClick={() => {}} // 클릭 핸들러 제거
                  onNodeHover={handleNodeHover}
                  onNodeDragEnd={(node) => {
                    // 드래그 종료 시 호버 해제
                    if (!hoveredNode || hoveredNode.id !== node.id) {
                      setHoveredNode(null);
                    }
                  }}
                  onBackgroundClick={() => {
                    setHoveredNode(null);
                  }}
                  enableNodeDrag={true}
                  enableZoomInteraction={true}
                  enablePanInteraction={true}
                  // 상호작용 강화 설정
                  nodePointerAreaPaint={(node, color, ctx) => {
                    // 노드 클릭 영역 확대
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(
                      node.x,
                      node.y,
                      getNodeSize(node) + 2,
                      0,
                      2 * Math.PI
                    );
                    ctx.fill();
                  }}
                  // 마우스 이벤트 활성화
                  onNodeRightClick={() => {}} // 우클릭 핸들러 제거
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
                  window.innerWidth - 500
                )}px`,
                top: `${Math.min(
                  tooltipPosition.y + 10,
                  window.innerHeight - 400
                )}px`,
                backgroundColor: COLORS.white,
                border: `1px solid ${COLORS.border}`,
                borderRadius: "12px",
                padding: "16px",
                maxWidth: "380px", // 최대 너비 증가
                minWidth: "280px", // 최소 너비 증가
                maxHeight: "80vh", // 최대 높이 설정
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.15)",
                zIndex: 10000,
                pointerEvents: "none",
                wordWrap: "break-word", // 긴 단어 줄바꿈
                whiteSpace: "pre-wrap", // 공백과 줄바꿈 유지
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
                <strong>{hoveredNode.name}</strong>
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
                        <strong>⭐ 초기 키워드 (Kiwi 추출)</strong>
                      </div>
                      <div
                        style={{
                          color: COLORS.dark,
                          fontSize: "10px",
                          lineHeight: "1.4",
                        }}
                      >
                        <strong>Kiwi 형태소 분석기로 추출된 명사</strong>
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
                        <strong>🔗 확장된 키워드 (LLM 확장)</strong>
                      </div>
                      <div style={{ color: COLORS.dark, fontSize: "10px" }}>
                        <strong>LLM으로 의미적 확장된 키워드</strong>
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
                        <strong>타입:</strong>
                      </span>
                      <span style={{ color: COLORS.gray }}>
                        <strong>
                          {hoveredNode.evidence.entityType || "Unknown"}
                        </strong>
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
                          <strong>연도:</strong>
                        </span>
                        <span style={{ color: COLORS.gray }}>
                          <strong>{hoveredNode.evidence.year}</strong>
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
                          <strong>Thread:</strong>
                        </span>
                        <span style={{ color: COLORS.gray, fontSize: "10px" }}>
                          <strong>{hoveredNode.evidence.threadType}</strong>
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
                          <strong>매칭 키워드: </strong>
                        </span>
                        <span style={{ color: COLORS.gray }}>
                          <strong>{hoveredNode.evidence.matchedKeyword}</strong>
                        </span>
                      </div>
                    )}

                    {hoveredNode.evidence.expansionMethod &&
                      hoveredNode.evidence.expansionMethod !== "none" && (
                        <div style={{ marginBottom: "4px" }}>
                          <span
                            style={{ fontWeight: "600", color: COLORS.dark }}
                          >
                            <strong>확장 방법: </strong>
                          </span>
                          <span style={{ color: COLORS.gray }}>
                            <strong>
                              {hoveredNode.evidence.expansionMethod}
                            </strong>
                          </span>
                        </div>
                      )}

                    {hoveredNode.evidence.matchMethod && (
                      <div>
                        <span style={{ fontWeight: "600", color: COLORS.dark }}>
                          <strong>매칭 방법: </strong>
                        </span>
                        <span style={{ color: COLORS.gray, fontSize: "10px" }}>
                          <strong>{hoveredNode.evidence.matchMethod}</strong>
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
                        <strong>요약:</strong>
                      </div>
                      <div style={{ color: COLORS.gray }}>
                        <strong>{hoveredNode.evidence.summary}</strong>
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
                          <strong>설명:</strong>
                        </div>
                        <div style={{ color: COLORS.gray }}>
                          <strong>{hoveredNode.evidence.description}</strong>
                        </div>
                      </div>
                    )}
                </>
              )}

              {/* 속성/관계 노드 (value 타입) 정보 표시 */}
              {/* 속성값 노드 정보 */}
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
                    <strong>📋 속성/관계 정보</strong>
                  </div>
                  {hoveredNode.evidence.entityName && (
                    <div
                      style={{
                        fontSize: "11px",
                        color: COLORS.dark,
                        marginBottom: "4px",
                      }}
                    >
                      <strong>엔티티:</strong>{" "}
                      <strong>{hoveredNode.evidence.entityName}</strong>
                    </div>
                  )}
                  {hoveredNode.evidence.predicate && (
                    <div
                      style={{
                        fontSize: "11px",
                        color: COLORS.dark,
                        marginBottom: "4px",
                      }}
                    >
                      <strong>Predicate:</strong>{" "}
                      <strong>{hoveredNode.evidence.predicate}</strong>
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
                      <strong>타입:</strong>{" "}
                      <strong>{hoveredNode.evidence.threadType}</strong>
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
                      <strong>값:</strong>
                      <br />
                      <span style={{ color: COLORS.gray }}>
                        <strong>{hoveredNode.evidence.description}</strong>
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 클릭 상세 정보 제거됨 - 호버 효과만 사용 */}
        </div>
      )}
    </div>
  );
};

export default EvidencePathView;
