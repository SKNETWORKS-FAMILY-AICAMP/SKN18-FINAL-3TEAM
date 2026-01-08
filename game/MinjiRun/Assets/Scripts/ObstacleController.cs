using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 장애물 컨트롤러
    /// 회전, 이동, 날아가기 등의 애니메이션 효과
    /// </summary>
    public class ObstacleController : MonoBehaviour
    {
        public enum FlyMode
        {
            None,           // 날아가지 않음
            Projectile,     // 발사형 (직선으로 날아감)
            TargetPlayer,   // 플레이어 추적형 (플레이어를 향해 일직선으로 날아감)
            LaneRush,       // 레인 돌진형 (특정 레인에서 플레이어를 향해 달려옴)
            Float,          // 부유형 (위아래로 떠다님)
            Wave,           // 파도형 (물결치듯 이동)
            Circle          // 원형 (원을 그리며 이동)
        }

        [Header("Rotation Animation")]
        [SerializeField] private bool rotate = false;
        [SerializeField] private Vector3 rotationSpeed = new Vector3(0f, 50f, 0f);

        [Header("Move Animation (왕복)")]
        [SerializeField] private bool move = false;
        [SerializeField] private Vector3 moveDirection = Vector3.right;
        [SerializeField] private float moveSpeed = 2f;
        [SerializeField] private float moveRange = 3f;

        [Header("Flying Settings")]
        [SerializeField] private FlyMode flyMode = FlyMode.None;
        [SerializeField] private Vector3 flyDirection = Vector3.forward;  // 날아가는 방향
        [SerializeField] private float flySpeed = 5f;                     // 날아가는 속도
        [SerializeField] private float floatAmplitude = 2f;               // 부유 높이
        [SerializeField] private float floatFrequency = 1f;               // 부유 주기
        [SerializeField] private float waveAmplitude = 2f;                // 파도 진폭
        [SerializeField] private float waveFrequency = 2f;                // 파도 주기
        [SerializeField] private float circleRadius = 3f;                 // 원형 반지름
        [SerializeField] private float circleSpeed = 2f;                  // 원형 속도
        [SerializeField] private bool destroyOnDistance = false;          // 거리 초과시 제거
        [SerializeField] private float maxDistance = 100f;                // 최대 거리
        [SerializeField] private float activationDelay = 0f;              // 활성화 지연 시간 (초)

        [Header("Lane Rush Settings")]
        [SerializeField] private int laneIndex = 1;                       // 레인 번호 (0=왼쪽, 1=중앙, 2=오른쪽)
        [SerializeField] private float laneWidth = 3f;                    // 레인 간격
        [SerializeField] private float rushSpeed = 15f;                   // 돌진 속도 (⚠️ Spawner가 SetupLaneRush로 덮어씀)

        private Vector3 startPosition;
        private float moveTimer = 0f;
        private float flyTimer = 0f;
        private Transform playerTransform;
        private Vector3 targetDirection;
        private bool isActivated = false;

        private void Start()
        {
            InitializeObstacle();
        }

        /// <summary>
        /// 장애물 초기화
        /// </summary>
        private void InitializeObstacle()
        {
            startPosition = transform.position;

            // 플레이어 찾기 (TargetPlayer 모드용)
            if (flyMode == FlyMode.TargetPlayer)
            {
                GameObject player = GameObject.FindGameObjectWithTag("Player");
                if (player != null)
                {
                    playerTransform = player.transform;
                }
            }

            // LaneRush 모드: 레인 위치로 이동
            if (flyMode == FlyMode.LaneRush)
            {
                float laneX = GetLanePosition(laneIndex);
                Vector3 lanePosition = transform.position;
                lanePosition.x = laneX;
                transform.position = lanePosition;
                startPosition = lanePosition;
            }

            // 활성화 지연이 있으면 지연 후 활성화
            if (activationDelay > 0f)
            {
                Invoke(nameof(ActivateFlight), activationDelay);
            }
            else
            {
                ActivateFlight();
            }
        }

        /// <summary>
        /// LaneRush 모드로 설정 (외부에서 호출)
        /// </summary>
        public void SetupLaneRush(int lane, float width, float speed)
        {
            flyMode = FlyMode.LaneRush;
            laneIndex = lane;
            laneWidth = width;
            rushSpeed = speed;
            destroyOnDistance = false;  // ⚠️ Spawner의 CleanupObstacles만 사용
            maxDistance = 100f;
            
            // 레인 위치로 이동
            float laneX = GetLanePosition(laneIndex);
            Vector3 lanePosition = transform.position;
            lanePosition.x = laneX;
            transform.position = lanePosition;
            startPosition = lanePosition;
            
            // 즉시 활성화
            isActivated = true;
            
            Debug.Log($"[ObstacleController] LaneRush setup: Lane={lane}, Speed={speed}, Position={transform.position}");
        }

        /// <summary>
        /// 일반 초기화 및 활성화 (외부에서 호출)
        /// </summary>
        public void InitializeAndActivate(Vector3 position, Vector3 rotation)
        {
            transform.position = position;
            transform.rotation = Quaternion.Euler(rotation);
            startPosition = position;
            isActivated = true;
        }

        /// <summary>
        /// Fly Mode 설정 (외부에서 호출)
        /// </summary>
        public void SetFlyMode(FlyMode mode)
        {
            flyMode = mode;
        }

        /// <summary>
        /// 레인 번호에 따른 X 위치 계산
        /// </summary>
        private float GetLanePosition(int lane)
        {
            // 레인 0 = 왼쪽, 1 = 중앙, 2 = 오른쪽
            return (lane - 1) * laneWidth;  // -laneWidth, 0, +laneWidth
        }

        /// <summary>
        /// 날아가기 활성화 (플레이어 방향 계산)
        /// </summary>
        private void ActivateFlight()
        {
            if (flyMode == FlyMode.TargetPlayer && playerTransform != null)
            {
                // 플레이어를 향한 방향 계산 (시작 시 한 번만)
                targetDirection = (playerTransform.position - transform.position).normalized;
            }

            isActivated = true;
        }

        private void Update()
        {
            // 회전 애니메이션
            if (rotate)
            {
                transform.Rotate(rotationSpeed * Time.deltaTime);
            }

            // 이동 애니메이션 (왕복) - flyMode가 None일 때만 작동
            if (move && flyMode == FlyMode.None)
            {
                moveTimer += Time.deltaTime * moveSpeed;
                float offset = Mathf.Sin(moveTimer) * moveRange;
                transform.localPosition = startPosition + moveDirection.normalized * offset;
            }

            // 날아가기 애니메이션
            HandleFlying();

            // 거리 체크 (너무 멀리 가면 제거)
            if (destroyOnDistance && Vector3.Distance(transform.position, startPosition) > maxDistance)
            {
                Destroy(gameObject);
            }
        }

        /// <summary>
        /// 날아가기 처리
        /// </summary>
        private void HandleFlying()
        {
            if (flyMode == FlyMode.None || !isActivated) return;

            flyTimer += Time.deltaTime;

            switch (flyMode)
            {
                case FlyMode.Projectile:
                    // 발사형: 직선으로 날아감
                    transform.position += flyDirection.normalized * flySpeed * Time.deltaTime;
                    break;

                case FlyMode.TargetPlayer:
                    // 플레이어 추적형: 플레이어를 향해 일직선으로 날아감
                    if (targetDirection != Vector3.zero)
                    {
                        transform.position += targetDirection * flySpeed * Time.deltaTime;

                        // 장애물이 플레이어를 향하도록 회전 (선택사항)
                        if (targetDirection != Vector3.zero)
                        {
                            Quaternion targetRotation = Quaternion.LookRotation(targetDirection);
                            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * 5f);
                        }
                    }
                    break;

                case FlyMode.LaneRush:
                    // 레인 돌진형: 특정 레인에서 플레이어를 향해 달려옴 (Z축으로만 이동)
                    Vector3 rushMovement = Vector3.back * rushSpeed * Time.deltaTime;  // 플레이어를 향해 (카메라 반대 방향)

                    // X 위치는 레인에 고정
                    Vector3 currentPos = transform.position;
                    currentPos.z += rushMovement.z;
                    currentPos.x = GetLanePosition(laneIndex);  // 레인 위치 유지
                    transform.position = currentPos;
                    break;

                case FlyMode.Float:
                    // 부유형: 앞으로 이동하면서 위아래로 떠다님
                    Vector3 floatMovement = flyDirection.normalized * flySpeed * Time.deltaTime;
                    float floatOffset = Mathf.Sin(flyTimer * floatFrequency) * floatAmplitude * Time.deltaTime;
                    transform.position += floatMovement + Vector3.up * floatOffset;
                    break;

                case FlyMode.Wave:
                    // 파도형: 앞으로 이동하면서 좌우로 물결침
                    Vector3 forwardMovement = flyDirection.normalized * flySpeed * Time.deltaTime;
                    Vector3 perpendicular = Vector3.Cross(flyDirection.normalized, Vector3.up).normalized;
                    float waveOffset = Mathf.Sin(flyTimer * waveFrequency) * waveAmplitude * Time.deltaTime;
                    transform.position += forwardMovement + perpendicular * waveOffset;
                    break;

                case FlyMode.Circle:
                    // 원형: 원을 그리며 이동
                    float angle = flyTimer * circleSpeed;
                    Vector3 circleOffset = new Vector3(
                        Mathf.Cos(angle) * circleRadius,
                        0f,
                        Mathf.Sin(angle) * circleRadius
                    );
                    transform.position = startPosition + circleOffset + flyDirection.normalized * flySpeed * flyTimer;
                    break;
            }
        }

        /// <summary>
        /// 플레이어와 충돌 시
        /// </summary>
        private void OnTriggerEnter(Collider other)
        {
            if (other.CompareTag("Player"))
            {
                // 넉백 적용
                RunnerController runner = other.GetComponent<RunnerController>();
                if (runner != null)
                {
                    Vector3 direction = other.transform.position - transform.position;
                    runner.ApplyKnockback(direction);
                }

                // 시간 5초 감소 ⭐
                if (GameTimerManager.Instance != null)
                {
                    GameTimerManager.Instance.SubtractTime(5f);
                    Debug.Log("[ObstacleController] Player hit obstacle! Time -5 seconds");
                }

                // 장애물 제거 (충돌 후 사라지게)
                Destroy(gameObject);
            }
        }
    }
}
