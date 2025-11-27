using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class AutoBlink : MonoBehaviour
{
    public SkinnedMeshRenderer targetFace;

    [Header("Target Settings")]
    [Tooltip("눈 감기 쉐이프키의 정확한 이름 (예: Fcl_EYE_Close)")]
    public string blinkShapeName = "Fcl_EYE_Close";

    [Header("Block Settings")]
    [Tooltip("이 표정들의 수치가 높으면 눈 깜빡임을 멈춤 (이름 입력)")]
    public List<string> preventShapeNames; 
    
    [Tooltip("표정 수치가 이 값 이상이면 깜빡임 차단 (기본 10)")]
    public float blockingThreshold = 10f; 

    [Header("Blink Settings")]
    public float intervalMin = 1.0f;
    public float intervalMax = 4.0f;
    public float blinkSpeed = 0.1f;

    // 내부적으로 사용할 캐싱된 인덱스 (성능 최적화)
    private int _cachedBlinkIndex = -1;
    private List<int> _cachedPreventIndices = new List<int>();
    private float currentBlinkWeight = 0f;

    void Start()
    {
        if (targetFace == null)
            targetFace = GetComponentInChildren<SkinnedMeshRenderer>();

        // [초기화] 문자열 이름을 인덱스 번호로 변환해서 캐싱
        InitializeIndices();
            
        StartCoroutine(BlinkRoutine());
    }

    void InitializeIndices()
    {
        if (targetFace == null || targetFace.sharedMesh == null) return;

        Mesh mesh = targetFace.sharedMesh;

        // 1. 눈 감기 인덱스 찾기
        _cachedBlinkIndex = mesh.GetBlendShapeIndex(blinkShapeName);
        if (_cachedBlinkIndex == -1) 
            Debug.LogError($"[AutoBlink] '{blinkShapeName}' 라는 쉐이프키를 찾을 수 없습니다! 이름을 확인하세요.");

        // 2. 차단 리스트 인덱스 찾기
        _cachedPreventIndices.Clear();
        foreach (string name in preventShapeNames)
        {
            int index = mesh.GetBlendShapeIndex(name);
            if (index != -1)
            {
                _cachedPreventIndices.Add(index);
            }
            else
            {
                Debug.LogWarning($"[AutoBlink] 차단 목록의 '{name}' 쉐이프키를 찾을 수 없습니다.");
            }
        }
    }

    void LateUpdate()
    {
        // 1. 기본 체크
        if (targetFace == null || _cachedBlinkIndex == -1) return;

        // 2. 현재 애니메이터(혹은 기존 상태)가 만들어둔 눈 값을 먼저 가져옵니다.
        // 예: Idle 상태라면 여기서 20이 들어옵니다.
        float animatorWeight = targetFace.GetBlendShapeWeight(_cachedBlinkIndex);

        // 3. 차단 여부 확인 (웃고 있거나 다른 표정일 때)
        foreach (int index in _cachedPreventIndices)
        {
            if (targetFace.GetBlendShapeWeight(index) > blockingThreshold)
            {
                // 차단된 상태라면 스크립트는 아무것도 건드리지 않고 빠져나갑니다.
                // (애니메이터가 웃는 표정을 짓게 놔둡니다)
                return; 
            }
        }

        // 4. 결과 적용 (핵심 수정!)
        // 애니메이터 값(20)과 깜빡임 값(0~100) 중 '더 많이 감은 쪽'을 선택합니다.
        // 평소: Max(20, 0) -> 20 유지
        // 깜빡일 때: Max(20, 100) -> 100으로 감김
        float finalWeight = Mathf.Max(animatorWeight, currentBlinkWeight);

        targetFace.SetBlendShapeWeight(_cachedBlinkIndex, finalWeight);
    }

    IEnumerator BlinkRoutine()
    {
        while (true)
        {
            float waitTime = Random.Range(intervalMin, intervalMax);
            yield return new WaitForSeconds(waitTime);

            // 눈 감기
            float t = 0;
            while (t < 1)
            {
                t += Time.deltaTime / blinkSpeed;
                currentBlinkWeight = Mathf.Lerp(0, 100, t);
                yield return null;
            }

            // 눈 뜨기
            while (t > 0)
            {
                t -= Time.deltaTime / blinkSpeed;
                currentBlinkWeight = Mathf.Lerp(0, 100, t);
                yield return null;
            }
            currentBlinkWeight = 0f;
        }
    }
}