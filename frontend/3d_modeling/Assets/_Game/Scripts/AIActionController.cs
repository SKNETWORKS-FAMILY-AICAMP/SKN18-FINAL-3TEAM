using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Text.RegularExpressions;

public class AIActionController : MonoBehaviour
{
    [Header("테스트 설정")]
    public float testInterval = 3.0f; // 동작 사이 대기 시간 (초)
    // 외부(DummyLLM)에서 호출할 함수
    public void PlayAllActionsSequence()
    {
        StartCoroutine(TestAllRoutine());
    }

    IEnumerator TestAllRoutine()
    {
        Debug.Log("🚀 [테스트 모드] 모든 액션 순회 시작!");

        // actionDatabase에 등록된 모든 태그를 하나씩 꺼냅니다.
        foreach (var data in actionDatabase)
        {
            Debug.Log($"▶ 테스트 실행 중: <{data.tagName}> ({data.type})");

            // 기존에 만들어둔 함수를 재활용합니다.
            ExecuteTag(data.tagName);

            // 중요: 애니메이션이 재생될 시간을 벌어줍니다.
            yield return new WaitForSeconds(testInterval);
        }

        Debug.Log("✅ [테스트 모드] 순회 종료!");
    }

    //---- 위에까지가 테스트 로직
    public SkinnedMeshRenderer faceMesh;
    public Animator bodyAnimator;
    public List<ActionTagData> actionDatabase; // DB 리스트

    private Dictionary<string, ActionTagData> tagMap;

    void Start()
    {
        tagMap = new Dictionary<string, ActionTagData>();
        foreach (var data in actionDatabase)
        {
            if (!tagMap.ContainsKey(data.tagName)) tagMap.Add(data.tagName, data);
        }
    }

    public void ProcessLLMResponse(string text)
    {
        Debug.Log($"[LLM]: {text}");
        MatchCollection matches = Regex.Matches(text, @"<([^>]+)>");
        foreach (Match match in matches) ExecuteTag(match.Groups[1].Value);
    }

    void ExecuteTag(string tagName)
    {
        if (tagMap.TryGetValue(tagName, out ActionTagData data))
        {
            if (data.type == ActionType.Face)
            {
                // 리스트에 있는 모든 표정을 동시에 실행
                foreach (var param in data.faceParams)
                {
                    StartCoroutine(ChangeFace(param.shapeName, param.intensity));
                }
            }
            else if (data.type == ActionType.Body)
            {
                bodyAnimator.SetTrigger(data.triggerName);
            }
        }
    }

    IEnumerator ChangeFace(string shapeName, float targetWeight)
    {
        int index = faceMesh.sharedMesh.GetBlendShapeIndex(shapeName);
        if (index == -1) yield break;
        float current = faceMesh.GetBlendShapeWeight(index);
        float elapsed = 0f;
        while (elapsed < 0.5f)
        {
            elapsed += Time.deltaTime;
            faceMesh.SetBlendShapeWeight(index, Mathf.Lerp(current, targetWeight, elapsed / 0.5f));
            yield return null;
        }
        faceMesh.SetBlendShapeWeight(index, targetWeight);
    }
}