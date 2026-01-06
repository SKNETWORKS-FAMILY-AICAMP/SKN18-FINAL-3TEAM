using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 플레이어를 따라가는 카메라 컨트롤러
    /// 부드러운 추적, 오프셋 설정 가능
    /// </summary>
    public class FollowCamera : MonoBehaviour
    {
        [Header("Target")]
        [SerializeField] private Transform target;  // 따라갈 대상 (플레이어)

        [Header("Camera Settings")]
        [SerializeField] private Vector3 offset = new Vector3(0f, 5f, -10f);  // 카메라 오프셋
        [SerializeField] private float smoothSpeed = 5f;  // 따라가기 속도
        [SerializeField] private bool lookAtTarget = true;  // 타겟을 바라볼지 여부

        [Header("Rotation")]
        [SerializeField] private bool allowRotation = false;  // 마우스로 회전 가능 여부
        [SerializeField] private float rotationSpeed = 5f;
        [SerializeField] private float minVerticalAngle = -30f;
        [SerializeField] private float maxVerticalAngle = 60f;

        [Header("Zoom")]
        [SerializeField] private bool allowZoom = false;  // 줌 인/아웃 가능 여부
        [SerializeField] private float zoomSpeed = 2f;
        [SerializeField] private float minDistance = 5f;
        [SerializeField] private float maxDistance = 15f;

        private Vector3 currentOffset;
        private float currentHorizontalAngle = 0f;
        private float currentVerticalAngle = 0f;

        private void Start()
        {
            // 타겟 자동 찾기
            if (target == null)
            {
                GameObject player = GameObject.FindGameObjectWithTag("Player");
                if (player != null)
                {
                    target = player.transform;
                }
            }

            // GameConfig에서 설정 로드
            if (GameStateManager.Instance != null && GameStateManager.Instance.Config != null)
            {
                GameConfig config = GameStateManager.Instance.Config;
                offset = config.cameraOffset;
                smoothSpeed = config.cameraSmoothSpeed;
            }

            currentOffset = offset;

            // 초기 각도 계산
            currentHorizontalAngle = 0f;
            currentVerticalAngle = Mathf.Atan2(offset.y, offset.z) * Mathf.Rad2Deg;
        }

        private void LateUpdate()
        {
            if (target == null) return;

            // 카메라 회전 처리
            if (allowRotation)
            {
                HandleRotation();
            }

            // 카메라 줌 처리
            if (allowZoom)
            {
                HandleZoom();
            }

            // 카메라 위치 업데이트
            UpdateCameraPosition();

            // 타겟 바라보기
            if (lookAtTarget)
            {
                transform.LookAt(target.position + Vector3.up * 1.5f);  // 약간 위를 바라봄
            }
        }

        /// <summary>
        /// 카메라 회전 처리 (마우스)
        /// </summary>
        private void HandleRotation()
        {
            // 마우스 우클릭 드래그로 회전
            if (Input.GetMouseButton(1))
            {
                currentHorizontalAngle += Input.GetAxis("Mouse X") * rotationSpeed;
                currentVerticalAngle -= Input.GetAxis("Mouse Y") * rotationSpeed;

                // 수직 각도 제한
                currentVerticalAngle = Mathf.Clamp(currentVerticalAngle, minVerticalAngle, maxVerticalAngle);

                // 오프셋 재계산
                Quaternion rotation = Quaternion.Euler(currentVerticalAngle, currentHorizontalAngle, 0f);
                currentOffset = rotation * new Vector3(0f, 0f, -offset.magnitude);
            }
        }

        /// <summary>
        /// 카메라 줌 처리 (마우스 휠)
        /// </summary>
        private void HandleZoom()
        {
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 0.01f)
            {
                float distance = currentOffset.magnitude;
                distance -= scroll * zoomSpeed;
                distance = Mathf.Clamp(distance, minDistance, maxDistance);

                currentOffset = currentOffset.normalized * distance;
            }
        }

        /// <summary>
        /// 카메라 위치 업데이트
        /// </summary>
        private void UpdateCameraPosition()
        {
            // 목표 위치 계산
            Vector3 desiredPosition = target.position + currentOffset;

            // 부드럽게 이동
            Vector3 smoothedPosition = Vector3.Lerp(transform.position, desiredPosition,
                smoothSpeed * Time.deltaTime);

            transform.position = smoothedPosition;
        }

        /// <summary>
        /// 타겟 설정
        /// </summary>
        public void SetTarget(Transform newTarget)
        {
            target = newTarget;
        }

        /// <summary>
        /// 오프셋 설정
        /// </summary>
        public void SetOffset(Vector3 newOffset)
        {
            offset = newOffset;
            currentOffset = newOffset;
        }

        #if UNITY_EDITOR
        /// <summary>
        /// 에디터에서 기즈모 표시
        /// </summary>
        private void OnDrawGizmosSelected()
        {
            if (target == null) return;

            // 카메라 위치와 타겟 연결선 표시
            Gizmos.color = Color.yellow;
            Gizmos.DrawLine(transform.position, target.position);

            // 타겟 위치 표시
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(target.position, 0.5f);

            // 목표 카메라 위치 표시
            Vector3 desiredPosition = target.position + offset;
            Gizmos.color = Color.cyan;
            Gizmos.DrawWireSphere(desiredPosition, 0.3f);
        }
        #endif
    }
}
