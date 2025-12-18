using UnityEngine;

public class DummyLLM : MonoBehaviour
{
    public AIActionController controller;
    [TextArea] public string testInput = "안녕? <joy> 반가워 <wave>";

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space)) 
        // controller.ProcessLLMResponse(testInput);
            // 전체 순회 테스트
            controller.PlayAllActionsSequence();
    }
}