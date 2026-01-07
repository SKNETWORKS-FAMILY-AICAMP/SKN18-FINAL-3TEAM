from langgraph.graph import StateGraph, END
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.nodes.classify_node import classify_node, route_classify
from backend.langgraph_structure1.nodes.generate_node import generate_node
from backend.langgraph_structure1.nodes.tone_adjust_node import tone_adjust_node, route_tone_adjust_node
from backend.langgraph_structure1.nodes.scene_split_node import scene_split_node
from backend.langgraph_structure1.rag.hybrid_node import hybrid_node
from backend.langgraph_structure1.nodes.extract_video_tag import extract_video_tag

# [병합 완료] 두 노드 모두 임포트
from backend.langgraph_structure1.nodes.background_gen_node import background_gen_node
from backend.langgraph_structure1.nodes.reaction_node import reaction_node
from backend.langgraph_structure1.nodes.thumbnail_gen_node import thumbnail_gen_node

def create_graph_flow():
    # 그래프에 사용할 변수 정의
    workflow = StateGraph(GraphState)

    # 1. 노드 추가 (모두 다 추가)
    workflow.add_node("classify_node", classify_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("tone_adjust_node", tone_adjust_node)
    workflow.add_node("scene_split_node", scene_split_node)
    workflow.add_node("hybrid_node", hybrid_node)
    workflow.add_node("extract_video_tag", extract_video_tag)
    
    # 신규 노드들 등록
    workflow.add_node("reaction_node", reaction_node)           # 리액션용
    workflow.add_node("background_gen_node", background_gen_node) # 배경 생성용
    workflow.add_node("thumbnail_gen_node", thumbnail_gen_node) # 썸네일 생성용

    # 2. 엣지(연결) 설정
    workflow.set_entry_point("classify_node")

    # [분기점 1] 분류 노드에서 갈림길
    # - 질문/영상 요청 -> hybrid_node
    # - 단순 리액션 -> reaction_node
    workflow.add_conditional_edges(
        "classify_node",
        route_classify,
        { 
            "hybrid_node": "hybrid_node",
            "reaction_node": "reaction_node",
        },
    )

    # [경로 A] 리액션 경로
    workflow.add_edge("reaction_node", END)

    # [경로 B] 영상 생성 경로
    workflow.add_edge("hybrid_node", "generate_node")
    workflow.add_edge("generate_node", "tone_adjust_node")

    # 말투 수정 검사 (안전장치 유지)
    workflow.add_conditional_edges(
        "tone_adjust_node",
        route_tone_adjust_node,
        { 
            "scene_split_node": "scene_split_node", # 성공 시 장면 분리로
            END: END,                               # 실패 시 종료
        },
    )

    # [병렬 실행] 장면 분리 -> 태그 추출 & 썸네일 생성 & 배경 생성 (모두 병렬) -> 종료
    # scene_split_node 이후 세 작업을 모두 병렬로 실행
    workflow.add_edge("scene_split_node", "extract_video_tag")
    workflow.add_edge("scene_split_node", "thumbnail_gen_node")
    workflow.add_edge("scene_split_node", "background_gen_node")
    
    # 세 병렬 작업이 모두 완료되면 종료
    workflow.add_edge("extract_video_tag", END)
    workflow.add_edge("thumbnail_gen_node", END)
    workflow.add_edge("background_gen_node", END)

    # 그래프 compile
    graph = workflow.compile()
    
    return graph

graph = create_graph_flow()