using UnityEngine;
using System.Collections.Generic;

public enum ActionType { Face, Body }

[System.Serializable]
public struct FaceParam // 표정 파라미터 구조체
{
    public string shapeName; // 쉐이프키 이름 (예: Fcl_EYE_Joy)
    [Range(0, 100)] public float intensity; // 강도 (0~100)
}

[CreateAssetMenu(fileName = "NewTag", menuName = "AI/Action Tag Data")]
public class ActionTagData : ScriptableObject
{
    public string tagName;      // LLM 태그 (예: joy)
    public ActionType type;
    
    [Header("Body 타입일 때만 사용")]
    public string triggerName;  // 애니메이터 트리거 이름
    
    [Header("Face 타입일 때만 사용 (여러 개 가능)")]
    public List<FaceParam> faceParams; // 리스트로 변경!
}