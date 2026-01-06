using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 골 지점 트리거
    /// EndPoint에 도달하면 게임 클리어
    /// </summary>
    public class GoalTrigger : MonoBehaviour
    {
        [Header("Trigger Settings")]
        [SerializeField] private Vector3 triggerSize = new Vector3(5f, 5f, 2f);  // 트리거 크기
        [SerializeField] private bool showGizmos = true;  // Scene 뷰에서 트리거 표시

        private BoxCollider triggerCollider;
        private bool hasTriggered = false;  // 중복 트리거 방지

        private void Awake()
        {
            SetupTrigger();
        }

        /// <summary>
        /// 트리거 설정
        /// </summary>
        private void SetupTrigger()
        {
            // Box Collider 추가 (없으면)
            triggerCollider = GetComponent<BoxCollider>();
            if (triggerCollider == null)
            {
                triggerCollider = gameObject.AddComponent<BoxCollider>();
            }

            // Trigger 설정
            triggerCollider.isTrigger = true;
            triggerCollider.size = triggerSize;

            Debug.Log("[GoalTrigger] Goal trigger setup complete");
        }

        private void OnTriggerEnter(Collider other)
        {
            // 이미 트리거되었으면 무시
            if (hasTriggered)
                return;

            // 플레이어만 감지
            if (other.CompareTag("Player"))
            {
                hasTriggered = true;
                Debug.Log("[GoalTrigger] Player reached the goal! Game Clear!");

                // 게임 클리어 처리
                if (GameStateManager.Instance != null)
                {
                    GameStateManager.Instance.GameClear();
                }
                else
                {
                    Debug.LogError("[GoalTrigger] GameStateManager instance not found!");
                }
            }
        }

        /// <summary>
        /// 트리거 리셋 (재시작 시 사용)
        /// </summary>
        public void ResetTrigger()
        {
            hasTriggered = false;
            Debug.Log("[GoalTrigger] Trigger reset!");
        }

        private void OnDrawGizmos()
        {
            if (!showGizmos)
                return;

            // Scene 뷰에서 골 지점 표시 (초록색)
            Gizmos.color = new Color(0f, 1f, 0f, 0.3f);
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.DrawCube(Vector3.zero, triggerSize);

            Gizmos.color = Color.green;
            Gizmos.DrawWireCube(Vector3.zero, triggerSize);
        }
    }
}
