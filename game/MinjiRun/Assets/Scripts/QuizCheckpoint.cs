using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 퀴즈 체크포인트 관리자 (싱글톤)
    /// 퀴즈 시작 시 플레이어 위치 저장, 오답 시 되돌리기
    /// </summary>
    public class QuizCheckpoint : MonoBehaviour
    {
        public static QuizCheckpoint Instance { get; private set; }

        [Header("Checkpoint Data")]
        [SerializeField] private Vector3 lastCheckpointPosition;
        [SerializeField] private Quaternion lastCheckpointRotation;
        [SerializeField] private bool hasCheckpoint = false;

        [Header("References")]
        [SerializeField] private Transform playerTransform;

        private void Awake()
        {
            // 싱글톤 설정
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
        }

        private void Start()
        {
            // 플레이어 찾기
            if (playerTransform == null)
            {
                GameObject player = GameObject.FindGameObjectWithTag("Player");
                if (player != null)
                {
                    playerTransform = player.transform;
                }
            }
        }

        /// <summary>
        /// 현재 위치를 체크포인트로 저장
        /// </summary>
        public void SaveCheckpoint()
        {
            if (playerTransform == null)
            {
                Debug.LogWarning("[QuizCheckpoint] Player not found!");
                return;
            }

            lastCheckpointPosition = playerTransform.position;
            lastCheckpointRotation = playerTransform.rotation;
            hasCheckpoint = true;

            Debug.Log($"[QuizCheckpoint] Checkpoint saved at {lastCheckpointPosition}");
        }

        /// <summary>
        /// 체크포인트 위치로 되돌리기 (오답 시)
        /// </summary>
        public void RestoreCheckpoint()
        {
            if (!hasCheckpoint)
            {
                Debug.LogWarning("[QuizCheckpoint] No checkpoint saved!");
                return;
            }

            if (playerTransform == null)
            {
                Debug.LogWarning("[QuizCheckpoint] Player not found!");
                return;
            }

            // 플레이어를 체크포인트로 이동
            CharacterController controller = playerTransform.GetComponent<CharacterController>();
            if (controller != null)
            {
                // CharacterController가 있으면 비활성화 후 이동
                controller.enabled = false;
                playerTransform.position = lastCheckpointPosition;
                playerTransform.rotation = lastCheckpointRotation;
                controller.enabled = true;
            }
            else
            {
                // CharacterController가 없으면 그냥 이동
                playerTransform.position = lastCheckpointPosition;
                playerTransform.rotation = lastCheckpointRotation;
            }

            // Rigidbody가 있으면 속도 초기화
            Rigidbody rb = playerTransform.GetComponent<Rigidbody>();
            if (rb != null)
            {
                rb.linearVelocity = Vector3.zero;
                rb.angularVelocity = Vector3.zero;
            }

            Debug.Log($"[QuizCheckpoint] Player restored to checkpoint at {lastCheckpointPosition}");
        }

        /// <summary>
        /// 체크포인트 리셋
        /// </summary>
        public void ResetCheckpoint()
        {
            hasCheckpoint = false;
            Debug.Log("[QuizCheckpoint] Checkpoint reset");
        }

        /// <summary>
        /// 특정 위치로 체크포인트 설정
        /// </summary>
        public void SaveCheckpointAt(Vector3 position, Quaternion rotation)
        {
            lastCheckpointPosition = position;
            lastCheckpointRotation = rotation;
            hasCheckpoint = true;
            Debug.Log($"[QuizCheckpoint] Checkpoint saved at {position}");
        }

        // 접근자
        public bool HasCheckpoint => hasCheckpoint;
        public Vector3 LastCheckpointPosition => lastCheckpointPosition;
        public Quaternion LastCheckpointRotation => lastCheckpointRotation;
    }
}
