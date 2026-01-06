using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 플레이어 러너 컨트롤러
    /// CharacterController 기반 3D 자유 이동/점프
    /// 키보드 입력 (WASD, 방향키, Space)
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class RunnerController : MonoBehaviour
    {
        [Header("Movement")]
        [SerializeField] private float moveSpeed = 5f;
        [SerializeField] private float jumpForce = 8f;
        [SerializeField] private float gravity = 20f;
        [SerializeField] private float rotationSpeed = 10f;
        [SerializeField] private int maxJumpCount = 2;  // 더블점프

        [Header("Dash")]
        [SerializeField] private float dashSpeed = 15f;              // 대쉬 속도
        [SerializeField] private float maxDashGauge = 100f;          // 최대 게이지
        [SerializeField] private float dashGaugeDepletionRate = 50f; // 게이지 소모 속도 (초당)
        [SerializeField] private float dashGaugeRecoveryRate = 25f;  // 게이지 회복 속도 (초당)
        [SerializeField] private float dashCooldownTime = 2f;        // 게이지 0일 때 회복 대기 시간 (초)

        [Header("Knockback")]
        [SerializeField] private float knockbackForce = 8f;          // 튕겨나가는 힘
        [SerializeField] private float knockbackUpwardForce = 4f;    // 위로 튕김
        [SerializeField] private float knockbackDuration = 0.2f;     // 지속 시간
        [SerializeField] private bool enableTumble = true;           // 넘어지는 효과 활성화
        [SerializeField] private float tumbleForce = 360f;           // 회전 속도 (도/초)
        [SerializeField] private float tumbleDuration = 0.5f;        // 회전 지속 시간

        [Header("Landing Dash (착지 대쉬)")]
        [SerializeField] private bool enableLandingDash = true;      // 착지 대쉬 활성화
        [SerializeField] private float landingDashWindow = 0.3f;     // 타이밍 윈도우 (착지 전후)
        [SerializeField] private float landingDashSpeed = 20f;       // 착지 대쉬 속도
        [SerializeField] private float landingDashDuration = 0.4f;   // 착지 대쉬 지속 시간

        [Header("Ground Check")]
        [SerializeField] private float groundCheckDistance = 0.2f;
        [SerializeField] private LayerMask groundLayer;
        [SerializeField] private float fallDeathY = -10f;  // 이 높이 이하로 떨어지면 자동 리스폰

        [Header("Animation (Optional)")]
        [SerializeField] private Animator animator;

        private CharacterController controller;
        private Vector3 moveDirection = Vector3.zero;
        private Vector3 velocity = Vector3.zero;
        private bool isGrounded = false;
        private bool canControl = true;
        private int jumpCount = 0;  // 현재 점프 횟수

        // 대쉬 관련
        private bool isDashing = false;
        private float dashGauge = 100f;  // 현재 게이지 (시작 시 풀충전)
        private Vector3 dashDirection = Vector3.zero;
        private bool canDash = true;  // Z 키를 떼었다가 다시 눌러야 대쉬 가능
        private float dashCooldownTimer = 0f;  // 쿨다운 타이머

        private Vector3 knockbackVelocity = Vector3.zero;
        private float knockbackTimer = 0f;
        private bool isTumbling = false;
        private float tumbleTimer = 0f;
        private Vector3 tumbleAxis = Vector3.zero;
        private Quaternion originalRotation = Quaternion.identity;
        
        // 착지 대쉬 관련
        private bool isKnockbacked = false;                  // 넉백 상태인지
        private bool landingDashInputPressed = false;        // 착지 대쉬 키 입력됨
        private bool wasGroundedLastFrame = false;           // 이전 프레임 지면 상태
        private bool isLandingDashing = false;               // 착지 대쉬 중인지
        private float landingDashTimer = 0f;                 // 착지 대쉬 타이머
        private Vector3 landingDashDirection = Vector3.zero; // 착지 대쉬 방향

        // 자동 전진 (테일즈런너 스타일)
        [Header("Auto Run")]
        [SerializeField] private bool autoRun = false;  // 자동 전진 비활성화
        [SerializeField] private float autoRunSpeed = 5f;

        private Vector3 lastPosition;
        private Vector3 lastSafePosition;  // 마지막 안전 위치 (낙사 시 리스폰용)

        private void Awake()
        {
            controller = GetComponent<CharacterController>();
        }

        private void Start()
        {
            // GameConfig에서 설정 로드 (Inspector 값이 기본값이면 GameConfig 사용)
            if (GameStateManager.Instance != null && GameStateManager.Instance.Config != null)
            {
                GameConfig config = GameStateManager.Instance.Config;

                // Inspector에서 기본값이 아니면 Inspector 값 우선
                // (Inspector에서 조정한 값을 유지)
                if (Mathf.Approximately(moveSpeed, 5f)) moveSpeed = config.moveSpeed;
                if (Mathf.Approximately(jumpForce, 8f)) jumpForce = config.jumpForce;
                if (Mathf.Approximately(gravity, 20f)) gravity = config.gravity;
                if (Mathf.Approximately(rotationSpeed, 10f)) rotationSpeed = config.rotationSpeed;
            }

            // 대쉬 게이지 초기화 (풀충전)
            dashGauge = maxDashGauge;

            // 게임 상태 변경 이벤트 구독
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.OnStateChanged += OnGameStateChanged;
            }

            lastPosition = transform.position;
            lastSafePosition = transform.position;  // 시작 위치를 안전 위치로 설정
        }

        private void OnDestroy()
        {
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.OnStateChanged -= OnGameStateChanged;
            }
        }

        private void Update()
        {
            // 넘어지는 효과 업데이트 (항상 실행)
            UpdateTumble();

            // Running 상태일 때만 컨트롤 가능
            if (!canControl || GameStateManager.Instance == null ||
                GameStateManager.Instance.CurrentState != GameState.Running)
            {
                return;
            }

            // 지면 체크
            CheckGroundStatus();

            // 착지 대쉬 처리 (지면 체크 직후)
            HandleLandingDash();

            // 낙사 체크 (Y 위치 기반)
            CheckFallDeath();

            // 입력 처리
            HandleDash();
            HandleMovement();
            HandleJump();

            // 이동 적용
            ApplyMovement();

            // 거리 계산 및 업데이트
            UpdateDistance();

            // 애니메이션 업데이트 (옵션)
            UpdateAnimation();

            // 이전 프레임 지면 상태 저장
            wasGroundedLastFrame = isGrounded;
        }

        /// <summary>
        /// 지면 체크
        /// </summary>
        private void CheckGroundStatus()
        {
            bool wasGrounded = isGrounded;
            isGrounded = controller.isGrounded;

            // CharacterController의 isGrounded가 신뢰성이 낮을 수 있어 추가 체크
            if (!isGrounded)
            {
                Ray ray = new Ray(transform.position + Vector3.up * 0.1f, Vector3.down);
                RaycastHit hit;
                isGrounded = Physics.Raycast(ray, out hit, groundCheckDistance + 0.1f, groundLayer);
            }

            // 지면에 있을 때 안전 위치 업데이트 (낙사 시 리스폰용)
            if (isGrounded)
            {
                // Y 위치가 -5보다 높을 때만 업데이트 (DeathZone은 보통 맵 아래에 있음)
                // 수동 맵에서는 모든 방향에서 안전 위치 업데이트 필요
                if (transform.position.y > -5f)
                {
                    // 거리 체크: 0.1m 이상 이동했을 때만 업데이트 (너무 자주 업데이트 방지)
                    float distance = Vector3.Distance(
                        new Vector3(lastSafePosition.x, 0, lastSafePosition.z),
                        new Vector3(transform.position.x, 0, transform.position.z)
                    );

                    if (distance > 0.1f)
                    {
                        lastSafePosition = transform.position;
                    }
                }
            }
        }

        /// <summary>
        /// 낙사 체크 (Y 위치 기반)
        /// </summary>
        private void CheckFallDeath()
        {
            // Y 위치가 fallDeathY 이하로 떨어지면 리스폰
            if (transform.position.y < fallDeathY)
            {
                RespawnToSafePosition();
            }
        }

        /// <summary>
        /// 이동 입력 처리 (방향키만 사용, WASD 비활성화)
        /// </summary>
        private void HandleMovement()
        {
            // 방향키만 사용 (WASD 비활성화)
            float horizontal = 0f;
            float vertical = 0f;

            if (Input.GetKey(KeyCode.LeftArrow)) horizontal = -1f;
            if (Input.GetKey(KeyCode.RightArrow)) horizontal = 1f;
            if (Input.GetKey(KeyCode.UpArrow)) vertical = 1f;
            if (Input.GetKey(KeyCode.DownArrow)) vertical = -1f;

            // 자동 전진 모드
            if (autoRun)
            {
                // 아무 키도 안 눌렀을 때만 자동 전진, 아래 키 누르면 뒤로 이동 가능
                if (vertical == 0f)
                {
                    vertical = 0.5f;  // 자동 전진
                }
                moveDirection = new Vector3(horizontal, 0f, vertical);
            }
            else
            {
                moveDirection = new Vector3(horizontal, 0f, vertical);
            }

            // 이동 방향 정규화
            if (moveDirection.magnitude > 1f)
            {
                moveDirection.Normalize();
            }

            // 카메라 방향 기준으로 이동 (옵션)
            // moveDirection = transform.TransformDirection(moveDirection);

            // 캐릭터 회전
            if (moveDirection != Vector3.zero)
            {
                Quaternion targetRotation = Quaternion.LookRotation(moveDirection);
                transform.rotation = Quaternion.Lerp(transform.rotation, targetRotation,
                    rotationSpeed * Time.deltaTime);
            }
        }

        /// <summary>
        /// 점프 입력 처리 (Ctrl 키, 더블점프 가능)
        /// </summary>
        private void HandleJump()
        {
            if (isGrounded)
            {
                // 지면에 있을 때 점프 카운트 리셋
                jumpCount = 0;

                // 지면에 있을 때 중력 리셋
                if (velocity.y < 0f)
                {
                    velocity.y = -2f;  // 약간의 downward force로 지면에 붙어있게
                }
            }

            // Ctrl 키로 점프 (더블점프 가능)
            if (Input.GetKeyDown(KeyCode.LeftControl) || Input.GetKeyDown(KeyCode.RightControl))
            {
                if (jumpCount < maxJumpCount)
                {
                    velocity.y = jumpForce;
                    jumpCount++;
                }
            }

            // 공중에 있을 때 중력 적용
            if (!isGrounded)
            {
                velocity.y -= gravity * Time.deltaTime;
            }
        }

        /// <summary>
        /// 대쉬 입력 처리 (Z 키 - 게이지 기반)
        /// </summary>
        private void HandleDash()
        {
            // 착지 대쉬 중일 때는 일반 대쉬 처리 안 함 (게이지 소모 방지)
            if (isLandingDashing)
            {
                isDashing = false;  // 일반 대쉬는 취소
                return;
            }

            // Z 키 입력 체크
            bool zKeyPressed = Input.GetKey(KeyCode.Z);

            // Z 키를 누르고 있고, 게이지가 있고, 대쉬 가능 상태이면 대쉬
            if (zKeyPressed && dashGauge > 0f && canDash)
            {
                isDashing = true;

                // 대쉬 중에도 방향 입력을 계속 반영 (방향 전환 가능)
                if (moveDirection.magnitude > 0.1f)
                {
                    dashDirection = moveDirection.normalized;
                }
                else if (!isDashing)
                {
                    // 처음 시작할 때만 전방으로 설정
                    dashDirection = transform.forward;
                }

                // 게이지 소모
                dashGauge -= dashGaugeDepletionRate * Time.deltaTime;
                if (dashGauge <= 0f)
                {
                    dashGauge = 0f;
                    canDash = false;  // 게이지가 0이 되면 대쉬 불가
                    dashCooldownTimer = dashCooldownTime;  // 쿨다운 시작
                }
            }
            else
            {
                // Z 키를 떼거나 게이지가 없거나 대쉬 불가 상태이면 대쉬 종료
                isDashing = false;

                // 쿨다운 타이머 감소
                if (dashCooldownTimer > 0f)
                {
                    dashCooldownTimer -= Time.deltaTime;
                    if (dashCooldownTimer <= 0f)
                    {
                        dashCooldownTimer = 0f;
                    }
                }

                // 쿨다운이 끝났으면 게이지 회복
                if (dashCooldownTimer <= 0f)
                {
                    dashGauge += dashGaugeRecoveryRate * Time.deltaTime;
                    if (dashGauge > maxDashGauge)
                    {
                        dashGauge = maxDashGauge;
                    }
                }

                // Z 키를 뗐으면 다시 대쉬 가능
                if (!zKeyPressed)
                {
                    canDash = true;
                }
            }
        }

        /// <summary>
        /// 이동 적용
        /// </summary>
        private void ApplyMovement()
        {
            Vector3 move;

            // 착지 대쉬 중일 때 (최우선)
            if (isLandingDashing)
            {
                move = landingDashDirection * landingDashSpeed;
            }
            // 대쉬 중일 때
            else if (isDashing)
            {
                move = dashDirection * dashSpeed;
            }
            else
            {
                // 일반 이동
                move = moveDirection * moveSpeed;
            }

            // 수직 이동 (중력, 점프)
            move.y = velocity.y;

            // 장애물에 맞았을 때 잠깐 튕김
            if (knockbackTimer > 0f)
            {
                move += knockbackVelocity;
                knockbackTimer -= Time.deltaTime;
            }

            // CharacterController로 이동
            controller.Move(move * Time.deltaTime);
        }

        /// <summary>
        /// 거리 업데이트
        /// </summary>
        private void UpdateDistance()
        {
            float distanceMoved = Vector3.Distance(
                new Vector3(transform.position.x, 0f, transform.position.z),
                new Vector3(lastPosition.x, 0f, lastPosition.z)
            );

            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.AddDistance(distanceMoved);
            }

            lastPosition = transform.position;
        }

        /// <summary>
        /// 애니메이션 업데이트
        /// </summary>
        private void UpdateAnimation()
        {
            if (animator == null) return;

            // 이동 속도
            float speed = moveDirection.magnitude;
            animator.SetFloat("Speed", speed);
            // 애니메이션 속도 비율
            float speedRatio = isDashing ? (dashSpeed / moveSpeed) : 1f;
            animator.SetFloat("AnimSpeed", Mathf.Clamp(speedRatio, 1f, 2f));

            // 지면 여부
            animator.SetBool("IsGrounded", isGrounded);

            // 점프 트리거
            if (!isGrounded && velocity.y > 0f)
            {
                animator.SetTrigger("Jump");
            }
        }
    
        /// <summary>
        /// 게임 상태 변경 시 호출
        /// </summary>
        private void OnGameStateChanged(GameState previousState, GameState newState)
        {
            // Quiz 상태일 때는 컨트롤 불가
            canControl = (newState == GameState.Running);
        }

        /// <summary>
        /// 장애물/오답문 충돌 처리
        /// </summary>
        private void OnControllerColliderHit(ControllerColliderHit hit)
        {
            // 오답 문 충돌 체크 (QuizDoor 컴포넌트가 있는 오브젝트)
            QuizDoor quizDoor = hit.gameObject.GetComponent<QuizDoor>();
            if (quizDoor != null && !quizDoor.IsCorrectAnswer)
            {
                // QuizDoor 스크립트에서 페널티 처리하도록 알림
                quizDoor.SendMessage("OnPlayerCollision", SendMessageOptions.DontRequireReceiver);
                return;
            }

            // 장애물 태그 체크
            if (hit.gameObject.CompareTag("Obstacle"))
            {
                Vector3 direction = transform.position - hit.transform.position;
                ApplyKnockback(direction);

                // 게임 오버 처리 (옵션)
                // GameStateManager.Instance.GameOver();
            }
        }

        /// <summary>
        /// 안전 위치로 리스폰
        /// </summary>
        private void RespawnToSafePosition()
        {
            // 즉시 스턴 시작 (떨어지는 동안 조작 불가)
            canControl = false;
            
            // CharacterController 비활성화 후 위치 변경
            controller.enabled = false;
            
            // Y 위치를 +2 높게 리스폰 (땅에 꺼지는 문제 방지)
            Vector3 respawnPosition = lastSafePosition;
            respawnPosition.y += 2f;
            transform.position = respawnPosition;
            
            controller.enabled = true;

            // 속도 초기화
            velocity = Vector3.zero;
            moveDirection = Vector3.zero;
            isDashing = false;
            canDash = true;
            dashCooldownTimer = 0f;

            // 1초 스턴 (떨어지는 동안 조작 불가 유지)
            StartCoroutine(RespawnStunCoroutine());
            
            Debug.Log($"[RunnerController] 리스폰! 위치: {respawnPosition}, 스턴 시작");
        }

        /// <summary>
        /// 리스폰 후 1초 스턴
        /// </summary>
        private System.Collections.IEnumerator RespawnStunCoroutine()
        {
            canControl = false;  // 조작 불가

            yield return new WaitForSeconds(1f);  // 1초 대기

            canControl = true;  // 조작 가능
        }

        /// <summary>
        /// 거리 계산 리셋 (재시작 시 호출)
        /// </summary>
        public void ResetDistance()
        {
            lastPosition = transform.position;
            Debug.Log("[RunnerController] Distance calculation reset!");
        }

        // 접근자
        public bool IsGrounded => isGrounded;
        public Vector3 Velocity => velocity;
        public bool IsDashing => isDashing;
        public float DashGauge => dashGauge;
        public float MaxDashGauge => maxDashGauge;
        public float DashGaugePercent => Mathf.Clamp01(dashGauge / maxDashGauge);

        public void ApplyKnockback(Vector3 direction)
        {
            if (knockbackTimer > 0f)
                return;

            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.0001f)
            {
                direction = -transform.forward;
            }

            // 뒤로 튕김
            knockbackVelocity = direction.normalized * knockbackForce;
            knockbackTimer = knockbackDuration;
            
            // 위로 크게 튕김 (더 높이!)
            if (knockbackUpwardForce > 0f)
            {
                velocity.y = knockbackUpwardForce;  // 기존 속도 무시하고 강제 점프
            }

            // 넘어지는 효과 (회전)
            if (enableTumble)
            {
                isTumbling = true;
                tumbleTimer = tumbleDuration;
                originalRotation = transform.rotation;
                
                // 회전 축: 옆으로 넘어지기 (X축) + 약간 비틀기 (Z축)
                tumbleAxis = new Vector3(1f, 0f, 0.3f).normalized;
                
                Debug.Log("[RunnerController] 💥 Knockback! 넘어지는 중...");
            }

            // 착지 대쉬 준비 상태
            isKnockbacked = true;
            landingDashInputPressed = false;
        }

        /// <summary>
        /// 착지 대쉬 처리
        /// </summary>
        private void HandleLandingDash()
        {
            // 착지 대쉬가 비활성화되어 있으면 스킵
            if (!enableLandingDash) return;

            // 착지 대쉬 중일 때 타이머 감소
            if (isLandingDashing)
            {
                landingDashTimer -= Time.deltaTime;
                if (landingDashTimer <= 0f)
                {
                    isLandingDashing = false;
                    Debug.Log("[RunnerController] ✅ 착지 대쉬 종료!");
                }
                return;
            }

            // 넉백 상태에서 Z키 입력 감지
            if (isKnockbacked && !isGrounded)
            {
                if (Input.GetKeyDown(KeyCode.Z))
                {
                    landingDashInputPressed = true;
                    Debug.Log("[RunnerController] ⏰ 착지 대쉬 입력! 타이밍을 맞춰보세요...");
                }
            }

            // 착지 순간 체크 (이전 프레임: 공중, 현재 프레임: 지면)
            if (!wasGroundedLastFrame && isGrounded)
            {
                // 넉백 상태에서 착지하고, Z키가 눌렸다면
                if (isKnockbacked && landingDashInputPressed)
                {
                    // 착지 대쉬 성공!
                    ExecuteLandingDash();
                }
                
                // 넉백 상태 해제
                isKnockbacked = false;
                landingDashInputPressed = false;
            }
        }

        /// <summary>
        /// 착지 대쉬 실행
        /// </summary>
        private void ExecuteLandingDash()
        {
            isLandingDashing = true;
            landingDashTimer = landingDashDuration;

            // 착지 대쉬 방향: 현재 이동 방향 또는 정면
            if (moveDirection.sqrMagnitude > 0.1f)
            {
                landingDashDirection = moveDirection.normalized;
            }
            else
            {
                landingDashDirection = transform.forward;
            }

            // 회전 즉시 복구 (착지 대쉬 시 바로 서기)
            if (isTumbling)
            {
                StopCoroutine(nameof(RecoverRotation));
                isTumbling = false;
                Vector3 euler = transform.eulerAngles;
                euler.x = 0f;
                euler.z = 0f;
                transform.eulerAngles = euler;
            }

            // 대쉬 게이지 소모 (선택사항)
            // dashGauge -= 20f;

            Debug.Log("[RunnerController] 🚀 착지 대쉬 성공! PERFECT!");
        }

        /// <summary>
        /// 넘어지는 효과 업데이트 (회전)
        /// </summary>
        private void UpdateTumble()
        {
            if (!isTumbling) return;

            tumbleTimer -= Time.deltaTime;

            if (tumbleTimer > 0f)
            {
                // 회전 적용
                float rotationAmount = tumbleForce * Time.deltaTime;
                transform.Rotate(tumbleAxis, rotationAmount, Space.Self);
            }
            else
            {
                // 회전 종료: 원래 회전으로 부드럽게 복귀
                isTumbling = false;
                StartCoroutine(RecoverRotation());
            }
        }

        /// <summary>
        /// 원래 회전으로 부드럽게 복귀
        /// </summary>
        private System.Collections.IEnumerator RecoverRotation()
        {
            float recoverTime = 0.3f;
            float elapsed = 0f;
            Quaternion startRotation = transform.rotation;

            while (elapsed < recoverTime)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / recoverTime;
                transform.rotation = Quaternion.Slerp(startRotation, Quaternion.Euler(0f, transform.eulerAngles.y, 0f), t);
                yield return null;
            }

            // 최종 정리: X와 Z 회전 완전히 0으로
            Vector3 euler = transform.eulerAngles;
            euler.x = 0f;
            euler.z = 0f;
            transform.eulerAngles = euler;

            Debug.Log("[RunnerController] ✅ 회복 완료!");
        }
    }
}
