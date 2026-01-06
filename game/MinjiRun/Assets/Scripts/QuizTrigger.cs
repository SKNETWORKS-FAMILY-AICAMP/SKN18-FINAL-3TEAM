using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 퀴즈 트리거
    /// 플레이어가 특정 거리에 도달하면 퀴즈 발동
    /// </summary>
    public class QuizTrigger : MonoBehaviour
    {
        [Header("Trigger Settings")]
        [SerializeField] private bool triggerOnce = true;  // 한 번만 트리거
        [SerializeField] private bool triggerOnEnter = true;  // 진입 시 트리거
        [SerializeField] private float cooldownTime = 5f;  // 재사용 대기 시간

        [Header("Quiz Door Reference")]
        [SerializeField] private QuizDoorController doorController;  // 이 트리거와 연결된 문 컨트롤러
        [Tooltip("자식 오브젝트에서 QuizDoorController를 자동으로 찾으려면 비워두세요")]

        [Header("Trigger Size")]
        [SerializeField] private Vector3 triggerSize = new Vector3(4f, 5f, 10f);  // 트리거 박스 크기 (Z축 크게 증가)
        [Tooltip("Z축을 크게 하면 빠르게 지나가도 감지 가능")]

        [Header("Detection Mode")]
        [SerializeField] private bool useBackupDetection = true;  // FixedUpdate로 백업 감지
        [Tooltip("OnTriggerEnter가 늦어도 FixedUpdate에서 플레이어 감지")]

        [Header("Visual (Optional)")]
        [SerializeField] private GameObject visualEffect;  // 트리거 시각 효과
        [SerializeField] private Color triggerColor = Color.yellow;

        private bool hasTriggered = false;
        private float lastTriggerTime = 0f;
        private Renderer triggerRenderer;
        private BoxCollider triggerCollider;
        private Transform playerTransform;

        private void Start()
        {
            // QuizDoorController가 할당되지 않았으면 자식 오브젝트에서 찾기
            if (doorController == null)
            {
                doorController = GetComponentInChildren<QuizDoorController>(true);
                if (doorController != null)
                {
                    Debug.Log($"[QuizTrigger] Found QuizDoorController in children: {doorController.name}");
                }
                else
                {
                    Debug.LogError("[QuizTrigger] ⚠️ No QuizDoorController found! Please assign or add as child.");
                }
            }

            // Box Collider 크기 설정
            triggerCollider = GetComponent<BoxCollider>();
            if (triggerCollider != null)
            {
                triggerCollider.size = triggerSize;
                triggerCollider.isTrigger = true;  // Trigger 모드 강제 활성화
                Debug.Log($"[QuizTrigger] Box Collider size set to: {triggerSize}");
            }
            else
            {
                Debug.LogError("[QuizTrigger] ⚠️ No Box Collider found! Please add a Box Collider component.");
            }

            // 플레이어 찾기 (백업 감지용)
            if (useBackupDetection)
            {
                GameObject player = GameObject.FindGameObjectWithTag("Player");
                if (player != null)
                {
                    playerTransform = player.transform;
                    Debug.Log($"[QuizTrigger] Player found for backup detection: {player.name}");
                }
                else
                {
                    Debug.LogWarning("[QuizTrigger] ⚠️ Player not found! Backup detection disabled.");
                }
            }

            // 시각 효과 설정
            triggerRenderer = GetComponent<Renderer>();
            if (triggerRenderer != null)
            {
                triggerRenderer.material.color = triggerColor;
            }
        }

        /// <summary>
        /// 백업 감지 (FixedUpdate - 물리 업데이트마다 체크)
        /// </summary>
        private void FixedUpdate()
        {
            // 백업 감지가 비활성화되어 있거나, 이미 트리거되었거나, 플레이어가 없으면 리턴
            if (!useBackupDetection || hasTriggered || playerTransform == null || triggerCollider == null)
                return;

            // 플레이어가 트리거 영역 안에 있는지 확인
            if (IsPlayerInsideTrigger())
            {
                Debug.Log("[QuizTrigger] 🔄 Backup detection triggered! (Player inside bounds)");
                TriggerQuiz();
            }
        }

        /// <summary>
        /// 플레이어가 트리거 영역 안에 있는지 확인
        /// </summary>
        private bool IsPlayerInsideTrigger()
        {
            // 트리거의 월드 공간 범위 계산
            Bounds triggerBounds = new Bounds(
                transform.position + triggerCollider.center,
                Vector3.Scale(triggerCollider.size, transform.lossyScale)
            );

            // 플레이어 위치가 범위 안에 있는지 확인
            return triggerBounds.Contains(playerTransform.position);
        }

        /// <summary>
        /// 플레이어 진입 시
        /// </summary>
        private void OnTriggerEnter(Collider other)
        {
            Debug.Log($"[QuizTrigger] ⭐ OnTriggerEnter called! Object: {other.name}, Tag: {other.tag}");

            if (!triggerOnEnter)
            {
                Debug.LogWarning("[QuizTrigger] ⚠️ triggerOnEnter is FALSE!");
                return;
            }

            if (other.CompareTag("Player"))
            {
                Debug.Log("[QuizTrigger] ✅ Player detected! Calling TriggerQuiz()");
                TriggerQuiz();
            }
            else
            {
                Debug.LogWarning($"[QuizTrigger] ⚠️ Not a Player! Tag: {other.tag}");
            }
        }

        /// <summary>
        /// 퀴즈 트리거
        /// </summary>
        private void TriggerQuiz()
        {
            Debug.Log("[QuizTrigger] ========== TriggerQuiz() called ==========");

            // 한 번만 트리거 체크
            if (triggerOnce && hasTriggered)
            {
                Debug.LogWarning("[QuizTrigger] ⚠️ Already triggered! (triggerOnce=true, hasTriggered=true)");
                return;
            }

            // 쿨다운 체크
            float timeSinceLastTrigger = Time.time - lastTriggerTime;
            if (timeSinceLastTrigger < cooldownTime)
            {
                Debug.LogWarning($"[QuizTrigger] ⚠️ Cooldown! ({timeSinceLastTrigger:F1}s / {cooldownTime}s)");
                return;
            }

            // 게임 상태 체크 (Running 상태일 때만)
            if (GameStateManager.Instance == null)
            {
                Debug.LogError("[QuizTrigger] ⚠️ GameStateManager.Instance is NULL!");
                return;
            }

            GameState currentState = GameStateManager.Instance.CurrentState;
            Debug.Log($"[QuizTrigger] Current GameState: {currentState}");

            if (currentState != GameState.Running)
            {
                Debug.LogWarning($"[QuizTrigger] ⚠️ Game is not in Running state! Current: {currentState}");
                return;
            }

            // QuizDoorController 체크
            if (doorController == null)
            {
                Debug.LogError("[QuizTrigger] ⚠️ No QuizDoorController assigned!");
                return;
            }

            // 퀴즈 시작 (게임은 계속 진행 - 플레이어 이동 가능)
            Debug.Log("[QuizTrigger] ✅ All checks passed! Starting quiz...");

            // 게임 상태를 Quiz로 변경하지 않음 (플레이어 계속 이동 가능)
            // GameStateManager.Instance.StartQuiz();  // ← 주석 처리: 게임 일시정지 제거

            // QuizManager에게 새 퀴즈 로드 요청 (이 트리거의 doorController와 함께)
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.StartNewQuiz(doorController);
                Debug.Log("[QuizTrigger] ✅ Quiz started successfully!");
            }
            else
            {
                Debug.LogError("[QuizTrigger] ⚠️ QuizManager.Instance is NULL!");
            }

            // 트리거 상태 업데이트
            hasTriggered = true;
            lastTriggerTime = Time.time;

            // 시각 효과 표시
            ShowVisualEffect();

            // 한 번만 트리거하는 경우 비활성화
            if (triggerOnce)
            {
                gameObject.SetActive(false);
                Debug.Log("[QuizTrigger] Trigger deactivated (triggerOnce=true)");
            }
        }

        /// <summary>
        /// 시각 효과 표시
        /// </summary>
        private void ShowVisualEffect()
        {
            if (visualEffect != null)
            {
                Instantiate(visualEffect, transform.position, Quaternion.identity);
            }
        }

        /// <summary>
        /// 트리거 리셋
        /// </summary>
        public void ResetTrigger()
        {
            hasTriggered = false;
            lastTriggerTime = 0f;
            gameObject.SetActive(true);
        }

        #if UNITY_EDITOR
        /// <summary>
        /// 에디터에서 기즈모 표시
        /// </summary>
        private void OnDrawGizmos()
        {
            Gizmos.color = hasTriggered ? Color.gray : triggerColor;
            Gizmos.DrawWireCube(transform.position, triggerSize);
        }
        #endif
    }
}
