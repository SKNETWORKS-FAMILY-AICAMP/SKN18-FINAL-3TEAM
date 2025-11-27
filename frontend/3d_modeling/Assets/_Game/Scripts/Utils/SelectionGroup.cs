//컴포넌트 우클릭 한 다음 맨 밑의 셀렉트 번개 버튼 누르면 리스트에 있는 컴포넌트들 자동 선택
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

public class SelectionGroup : MonoBehaviour
{
    // 여기에 뼈들을 드래그해서 넣어두세요 (한 번만!)
    public GameObject[] myBones;

    // 인스펙터 컴포넌트 우클릭 -> "Select This Group" 누르면 실행됨
    [ContextMenu("Select This Group ⚡")]
    void Select()
    {
#if UNITY_EDITOR
        if (myBones != null && myBones.Length > 0)
        {
            Selection.objects = myBones; // 유니티 에디터의 현재 선택을 이것들로 바꿈
            Debug.Log($"⚡ {myBones.Length}개 뼈 선택 완료!");
        }
#endif
    }
}