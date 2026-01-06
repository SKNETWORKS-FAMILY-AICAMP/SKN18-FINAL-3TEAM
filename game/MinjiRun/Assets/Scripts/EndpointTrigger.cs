using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 게임 클리어 지점 (Endpoint) 트리거
    /// 플레이어가 이 지점에 도착하면 게임 클리어
    /// </summary>
    public class EndpointTrigger : MonoBehaviour
    {
        [Header("Endpoint Settings")]
        [SerializeField] private bool showDebugMessages = true;

        [Header("Visual Feedback (Optional)")]
        [SerializeField] private ParticleSystem clearEffect;  // 클리어 이펙트 (선택사항)
        [SerializeField] private AudioClip clearSound;        // 클리어 사운드 (선택사항)

        private bool hasTriggered = false;  // 한 번만 트리거되도록

        private void Start()
        {
            // BoxCollider가 Trigger로 설정되어 있는지 확인
            BoxCollider boxCollider = GetComponent<BoxCollider>();
            if (boxCollider == null)
            {
                Debug.LogError("[EndpointTrigger] BoxCollider가 없습니다! BoxCollider를 추가하고 Is Trigger를 체크하세요.");
            }
            else if (!boxCollider.isTrigger)
            {
                Debug.LogWarning("[EndpointTrigger] BoxCollider의 Is Trigger가 체크되어 있지 않습니다. 자동으로 활성화합니다.");
                boxCollider.isTrigger = true;
            }
        }

        /// <summary>
        /// 플레이어가 Endpoint에 도착했을 때
        /// </summary>
        private void OnTriggerEnter(Collider other)
        {
            // 이미 트리거되었으면 무시
            if (hasTriggered)
                return;

            // 플레이어인지 확인
            if (!other.CompareTag("Player"))
                return;

            hasTriggered = true;

            if (showDebugMessages)
            {
                Debug.Log("[EndpointTrigger] 플레이어가 Endpoint에 도착했습니다! 게임 클리어!");
            }

            // 이펙트 재생 (있으면)
            if (clearEffect != null)
            {
                clearEffect.Play();
            }

            // 사운드 재생 (있으면)
            if (clearSound != null)
            {
                AudioSource audioSource = GetComponent<AudioSource>();
                if (audioSource == null)
                {
                    audioSource = gameObject.AddComponent<AudioSource>();
                }
                audioSource.PlayOneShot(clearSound);
            }

            // 게임 클리어 처리
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.GameClear();
            }
            else
            {
                Debug.LogError("[EndpointTrigger] GameStateManager를 찾을 수 없습니다!");
            }
        }

        /// <summary>
        /// 트리거 리셋 (재시작 시 사용)
        /// </summary>
        public void ResetTrigger()
        {
            hasTriggered = false;
            Debug.Log("[EndpointTrigger] Trigger reset!");
        }

        /// <summary>
        /// Gizmo로 Endpoint 영역 표시 (Scene View에서만 보임)
        /// </summary>
        private void OnDrawGizmos()
        {
            BoxCollider boxCollider = GetComponent<BoxCollider>();
            if (boxCollider != null)
            {
                Gizmos.color = new Color(0f, 1f, 0f, 0.3f);  // 초록색 반투명
                Gizmos.matrix = transform.localToWorldMatrix;
                Gizmos.DrawCube(boxCollider.center, boxCollider.size);

                Gizmos.color = Color.green;
                Gizmos.DrawWireCube(boxCollider.center, boxCollider.size);
            }
        }

        /// <summary>
        /// 선택되었을 때 Gizmo 표시 (Scene View에서만 보임)
        /// </summary>
        private void OnDrawGizmosSelected()
        {
            BoxCollider boxCollider = GetComponent<BoxCollider>();
            if (boxCollider != null)
            {
                Gizmos.color = new Color(0f, 1f, 0f, 0.5f);  // 더 진한 초록색
                Gizmos.matrix = transform.localToWorldMatrix;
                Gizmos.DrawCube(boxCollider.center, boxCollider.size);
            }
        }
    }
}
