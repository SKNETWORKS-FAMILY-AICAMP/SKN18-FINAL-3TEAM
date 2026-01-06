using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace minji_run
{
    /// <summary>
    /// Quiz Panel 자동 진단 및 수정 스크립트
    /// Quiz Panel GameObject에 이 스크립트를 추가하세요
    /// </summary>
    public class QuizPanelDiagnostic : MonoBehaviour
    {
        private void Start()
        {
            Debug.Log("====== [Quiz Panel Diagnostic] 시작 ======");
            DiagnoseAndFix();
        }

        private void OnEnable()
        {
            Debug.Log($"[Quiz Panel Diagnostic] Quiz Panel이 활성화되었습니다! Time: {Time.time}");

            // 활성화될 때마다 진단
            DiagnoseAndFix();
        }

        private void DiagnoseAndFix()
        {
            // 1. GameObject 활성화 상태 확인
            Debug.Log($"[Quiz Panel] GameObject.activeSelf: {gameObject.activeSelf}");
            Debug.Log($"[Quiz Panel] GameObject.activeInHierarchy: {gameObject.activeInHierarchy}");

            // 2. RectTransform 확인
            RectTransform rectTransform = GetComponent<RectTransform>();
            if (rectTransform != null)
            {
                Debug.Log($"[Quiz Panel] RectTransform 위치: {rectTransform.anchoredPosition}");
                Debug.Log($"[Quiz Panel] RectTransform 크기: {rectTransform.sizeDelta}");
                Debug.Log($"[Quiz Panel] RectTransform 스케일: {rectTransform.localScale}");
                Debug.Log($"[Quiz Panel] RectTransform Anchors - Min: {rectTransform.anchorMin}, Max: {rectTransform.anchorMax}");

                // 스케일이 0이면 수정
                if (rectTransform.localScale == Vector3.zero)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ Scale이 0입니다! (1, 1, 1)로 수정합니다.");
                    rectTransform.localScale = Vector3.one;
                }

                // 크기가 0이면 수정
                if (rectTransform.sizeDelta == Vector2.zero &&
                    rectTransform.anchorMin == rectTransform.anchorMax)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ 크기가 0입니다! Stretch로 설정합니다.");
                    rectTransform.anchorMin = Vector2.zero;
                    rectTransform.anchorMax = Vector2.one;
                    rectTransform.offsetMin = Vector2.zero;
                    rectTransform.offsetMax = Vector2.zero;
                }
            }

            // 3. Image 컴포넌트 확인
            Image image = GetComponent<Image>();
            if (image != null)
            {
                Debug.Log($"[Quiz Panel] Image.enabled: {image.enabled}");
                Debug.Log($"[Quiz Panel] Image.color: {image.color}");
                Debug.Log($"[Quiz Panel] Image.color.a (Alpha): {image.color.a}");
                Debug.Log($"[Quiz Panel] Image.sprite: {(image.sprite != null ? image.sprite.name : "NULL")}");

                // Alpha가 0이면 수정
                if (image.color.a < 0.01f)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ Alpha가 0입니다! 반투명 검정색으로 변경합니다.");
                    image.color = new Color(0f, 0f, 0f, 0.8f);  // 반투명 검정
                }

                // Image가 비활성화되어 있으면 활성화
                if (!image.enabled)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ Image 컴포넌트가 비활성화되어 있습니다! 활성화합니다.");
                    image.enabled = true;
                }
            }
            else
            {
                Debug.LogWarning("[Quiz Panel] ⚠️ Image 컴포넌트가 없습니다!");
            }

            // 4. CanvasGroup 확인
            CanvasGroup canvasGroup = GetComponent<CanvasGroup>();
            if (canvasGroup != null)
            {
                Debug.Log($"[Quiz Panel] CanvasGroup.alpha: {canvasGroup.alpha}");
                Debug.Log($"[Quiz Panel] CanvasGroup.interactable: {canvasGroup.interactable}");
                Debug.Log($"[Quiz Panel] CanvasGroup.blocksRaycasts: {canvasGroup.blocksRaycasts}");

                // Alpha가 0이면 수정
                if (canvasGroup.alpha < 0.01f)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ CanvasGroup Alpha가 0입니다! 1로 변경합니다.");
                    canvasGroup.alpha = 1f;
                }
            }

            // 5. Canvas 계층 확인
            Canvas parentCanvas = GetComponentInParent<Canvas>();
            if (parentCanvas != null)
            {
                Debug.Log($"[Quiz Panel] 부모 Canvas: {parentCanvas.name}");
                Debug.Log($"[Quiz Panel] Canvas.enabled: {parentCanvas.enabled}");
                Debug.Log($"[Quiz Panel] Canvas.renderMode: {parentCanvas.renderMode}");

                if (parentCanvas.renderMode == RenderMode.ScreenSpaceCamera)
                {
                    Debug.Log($"[Quiz Panel] Canvas.worldCamera: {(parentCanvas.worldCamera != null ? parentCanvas.worldCamera.name : "NULL")}");
                }
            }
            else
            {
                Debug.LogError("[Quiz Panel] ⚠️ 부모 Canvas를 찾을 수 없습니다!");
            }

            // 6. 자식 QuestionText 확인
            TextMeshProUGUI questionText = GetComponentInChildren<TextMeshProUGUI>();
            if (questionText != null)
            {
                Debug.Log($"[Quiz Panel] QuestionText 발견: {questionText.name}");
                Debug.Log($"[Quiz Panel] QuestionText.enabled: {questionText.enabled}");
                Debug.Log($"[Quiz Panel] QuestionText.color: {questionText.color}");
                Debug.Log($"[Quiz Panel] QuestionText.color.a (Alpha): {questionText.color.a}");
                Debug.Log($"[Quiz Panel] QuestionText.text: {questionText.text}");
                Debug.Log($"[Quiz Panel] QuestionText GameObject.activeSelf: {questionText.gameObject.activeSelf}");
                Debug.Log($"[Quiz Panel] QuestionText.fontSize: {questionText.fontSize}");
                Debug.Log($"[Quiz Panel] QuestionText.font: {(questionText.font != null ? questionText.font.name : "NULL")}");

                // QuestionText가 비활성화되어 있으면 활성화
                if (!questionText.gameObject.activeSelf)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ QuestionText GameObject가 비활성화되어 있습니다! 활성화합니다.");
                    questionText.gameObject.SetActive(true);
                }

                // QuestionText 컴포넌트가 비활성화되어 있으면 활성화
                if (!questionText.enabled)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ QuestionText 컴포넌트가 비활성화되어 있습니다! 활성화합니다.");
                    questionText.enabled = true;
                }

                // Alpha가 0이면 수정 (가장 흔한 문제!)
                if (questionText.color.a < 0.01f)
                {
                    Debug.LogWarning("[Quiz Panel] ⚠️ QuestionText Alpha가 0입니다! 흰색(Alpha 255)으로 변경합니다.");
                    questionText.color = Color.white;  // 흰색, Alpha 1
                }

                // 폰트 사이즈가 너무 작으면 수정
                if (questionText.fontSize < 20f)
                {
                    Debug.LogWarning($"[Quiz Panel] ⚠️ QuestionText 폰트 사이즈가 너무 작습니다! ({questionText.fontSize}) → 48로 변경합니다.");
                    questionText.fontSize = 48f;
                }

                // 테스트 텍스트 설정 (한글 + 영어)
                if (string.IsNullOrEmpty(questionText.text) || questionText.text == "질문이 여기에 표시됩니다")
                {
                    Debug.Log("[Quiz Panel] 테스트 텍스트를 설정합니다.");
                    questionText.text = "테스트 질문입니다 (Test Question)";
                }
            }
            else
            {
                Debug.LogWarning("[Quiz Panel] ⚠️ 자식 QuestionText를 찾을 수 없습니다!");
            }

            Debug.Log("====== [Quiz Panel Diagnostic] 완료 ======");
        }

        private void Update()
        {
            // 매 프레임 간단한 상태 출력 (처음 5초간만)
            if (Time.time < 5f && Time.frameCount % 60 == 0)  // 1초마다
            {
                Debug.Log($"[Quiz Panel] Update - Active: {gameObject.activeSelf}, Time: {Time.time:F1}");
            }
        }
    }
}
