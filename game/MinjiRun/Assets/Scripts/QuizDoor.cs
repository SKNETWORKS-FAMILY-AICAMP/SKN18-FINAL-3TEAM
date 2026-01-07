using UnityEngine;
using TMPro;

namespace minji_run
{
    /// <summary>
    /// 개별 퀴즈 문
    /// 플레이어가 통과하면 답안 제출
    /// </summary>
    public class QuizDoor : MonoBehaviour
    {
        [Header("Door Settings")]
        [SerializeField] private int choiceIndex;          // 이 문이 몇 번째 선택지인지 (0, 1, 2)
        [SerializeField] private string choiceText;        // 선택지 텍스트
        [SerializeField] private bool isCorrectAnswer;     // 정답 여부

        [Header("UI References")]
        [SerializeField] private TextMeshPro choiceLabel;  // 3D 텍스트

        [Header("Visual Settings")]
        [SerializeField] private Color normalColor = Color.white;
        [SerializeField] private Color correctColor = Color.green;
        [SerializeField] private Color wrongColor = Color.red;

        [Header("Portal Effect")]
        [SerializeField] private GameObject portalEffect;  // 문 사이 포털 이펙트 (Quad)
        [Tooltip("문 사이 통과 영역의 색깔 평면 (자식에서 'Portal' 이름으로 자동 찾기)")]

        private MeshRenderer portalRenderer;  // 포털 렌더러
        private bool hasBeenSelected = false;
        private bool hasPenaltyApplied = false;  // 페널티가 한 번만 적용되도록
        private bool hasBeenUsedPermanently = false;  // 이 문이 한 번이라도 사용되었는지 (영구적, 게임 재시작 전까지 유지)
        private QuizDoorController myController;  // 이 문을 관리하는 컨트롤러 (Initialize 시 설정)

        private void Awake()
        {
            // 포털 이펙트 자동 찾기 (Portal 이름의 자식 오브젝트)
            if (portalEffect == null)
            {
                Transform portalTransform = transform.Find("Portal");
                if (portalTransform != null)
                {
                    portalEffect = portalTransform.gameObject;
                }
            }

            // 포털 렌더러 가져오기
            if (portalEffect != null)
            {
                portalRenderer = portalEffect.GetComponent<MeshRenderer>();
            }
        }

        /// <summary>
        /// 문 초기화
        /// </summary>
        public void Initialize(int index, string text, bool isCorrect, QuizDoorController controller)
        {
            // 이미 사용된 문이면 초기화 거부
            if (hasBeenUsedPermanently)
            {
                Debug.LogWarning($"[QuizDoor] {gameObject.name} 이미 사용된 문입니다. 초기화 거부!");
                // Collider는 이미 비활성화되어 있으므로 추가 처리 불필요
                return;
            }

            choiceIndex = index;
            choiceText = text;
            isCorrectAnswer = isCorrect;
            myController = controller;  // 컨트롤러 참조 저장

            // 문 활성화 (혹시 비활성화되어 있었다면)
            gameObject.SetActive(true);

            if (choiceLabel == null)
            {
                choiceLabel = GetComponentInChildren<TextMeshPro>(true);
            }

            // 텍스트 표시
            if (choiceLabel != null)
            {
                choiceLabel.text = choiceText;
                Debug.Log($"[QuizDoor] {gameObject.name} Initialize: index={index}, text='{choiceText}', isCorrect={isCorrect}");
            }
            else
            {
                Debug.LogError($"[QuizDoor] {gameObject.name} choiceLabel이 null입니다! 텍스트를 표시할 수 없습니다.");
            }

            // 초기 포털 색상 (흰색)
            SetPortalColor(normalColor);

            // Collider 설정: 정답 문은 Trigger, 오답 문은 Solid
            BoxCollider collider = GetComponent<BoxCollider>();
            if (collider != null)
            {
                collider.enabled = true;  // Collider 활성화
                collider.isTrigger = isCorrect;  // 정답: Trigger (통과 가능), 오답: Solid (막힘)
            }

            // 현재 퀴즈용 플래그만 리셋 (영구 플래그는 유지)
            hasBeenSelected = false;
            hasPenaltyApplied = false;
        }

        /// <summary>
        /// 플레이어가 정답 문을 통과했을 때 (Trigger)
        /// </summary>
        private void OnTriggerEnter(Collider other)
        {
            Debug.Log($"[QuizDoor] {gameObject.name} OnTriggerEnter: {other.name}, isCorrectAnswer={isCorrectAnswer}, hasBeenSelected={hasBeenSelected}");

            if (!other.CompareTag("Player"))
                return;

            // 정답 문만 처리 (오답 문은 Solid이므로 OnPlayerCollision에서 처리)
            if (isCorrectAnswer && !hasBeenSelected)
            {
                hasBeenSelected = true;
                // 영구 사용 표시는 QuizDoorController에서 처리 (그룹 단위로)

                // 포털 색상 변경 (초록색)
                SetPortalColor(correctColor);

                // QuizManager에 정답 제출 (자신의 참조 + 컨트롤러 참조 전달)
                if (QuizManager.Instance != null)
                {
                    Debug.Log($"[QuizDoor] {gameObject.name} SubmitAnswer 호출! Controller: {myController?.gameObject.name}");
                    QuizManager.Instance.SubmitAnswer(choiceIndex, this, myController);
                }
                else
                {
                    Debug.LogError("[QuizDoor] QuizManager.Instance is NULL!");
                }

                Debug.Log($"[QuizDoor] {gameObject.name} 정답 문 통과!");
            }
            else
            {
                Debug.LogWarning($"[QuizDoor] {gameObject.name} 조건 불만족: isCorrectAnswer={isCorrectAnswer}, hasBeenSelected={hasBeenSelected}");
            }
        }

        /// <summary>
        /// 이 문을 영구적으로 사용 불가 상태로 만듦 (QuizDoorController에서 호출)
        /// </summary>
        public void MarkAsUsedPermanently()
        {
            hasBeenUsedPermanently = true;

            // 문을 비활성화하거나 Collider를 제거하여 통과 불가능하게 만듦
            BoxCollider collider = GetComponent<BoxCollider>();
            if (collider != null)
            {
                collider.enabled = false;  // Collider 비활성화 (통과도 충돌도 안됨)
            }

            Debug.Log($"[QuizDoor] {gameObject.name} 영구적으로 사용 불가 처리!");
        }

        /// <summary>
        /// 플레이어가 오답 문에 부딪혔을 때 (RunnerController에서 호출)
        /// </summary>
        private void OnPlayerCollision()
        {
            // 오답 문만 처리 (정답 문은 Trigger이므로 OnTriggerEnter에서 처리)
            if (!isCorrectAnswer && !hasPenaltyApplied)
            {
                hasPenaltyApplied = true;  // 페널티 한 번만 적용

                // 포털 색상 변경 (빨간색)
                SetPortalColor(wrongColor);

                // 페널티 시간 감소 (한 번만)
                if (GameTimerManager.Instance != null)
                {
                    GameTimerManager.Instance.ApplyPenalty();
                }
            }
        }


        /// <summary>
        /// 정답 문 강조 표시
        /// </summary>
        public void ShowCorrectAnswer()
        {
            if (isCorrectAnswer)
            {
                SetPortalColor(correctColor);
            }
        }

        /// <summary>
        /// 문 상태 리셋 (다음 퀴즈를 위해)
        /// </summary>
        public void ResetDoor()
        {
            // 영구적으로 사용된 문이면 비활성화 상태 유지
            if (hasBeenUsedPermanently)
            {
                // Collider가 이미 비활성화되어 있으므로 추가 처리 불필요
                return;
            }

            hasBeenSelected = false;
            hasPenaltyApplied = false;

            // 포털 색상 초기화
            SetPortalColor(normalColor);

            // 텍스트는 Initialize()에서 다시 설정되므로 여기서 지우지 않음
            // (텍스트를 지우면 다음 세그먼트에 영향을 줄 수 있음)
        }

        /// <summary>
        /// 게임 재시작 시 완전히 리셋 (영구 플래그 포함)
        /// </summary>
        public void FullReset()
        {
            hasBeenSelected = false;
            hasPenaltyApplied = false;
            hasBeenUsedPermanently = false;

            // 문 다시 활성화
            gameObject.SetActive(true);

            // Collider 다시 활성화
            BoxCollider collider = GetComponent<BoxCollider>();
            if (collider != null)
            {
                collider.enabled = true;
            }

            // 포털 색상 초기화
            SetPortalColor(normalColor);

            Debug.Log($"[QuizDoor] {gameObject.name} 완전 리셋!");
        }

        /// <summary>
        /// 포털 색상 변경 (문 사이 통과 영역)
        /// </summary>
        private void SetPortalColor(Color color)
        {
            if (portalRenderer != null)
            {
                // Material의 색상 변경 (URP와 Built-in 모두 지원)
                portalRenderer.material.color = color;

                // URP의 경우 _BaseColor도 설정
                if (portalRenderer.material.HasProperty("_BaseColor"))
                {
                    portalRenderer.material.SetColor("_BaseColor", color);
                }
            }
        }

        // 접근자
        public int ChoiceIndex => choiceIndex;
        public string ChoiceText => choiceText;
        public bool IsCorrectAnswer => isCorrectAnswer;
    }
}
