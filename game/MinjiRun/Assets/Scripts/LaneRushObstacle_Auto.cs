using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// AutoLaneCalculator를 사용하는 레인 러쉬 장애물
    /// 트랙 넓이에 맞춰 자동으로 레인 위치 계산
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    public class LaneRushObstacle_Auto : MonoBehaviour
    {
        [Header("Lane Calculator Reference")]
        [SerializeField] private AutoLaneCalculator laneCalculator;
        [Tooltip("레인 위치를 계산할 AutoLaneCalculator (Managers에 있음)")]

        [Header("Lane Settings")]
        [SerializeField] private int laneIndex = 1;  // 0=왼쪽, 1=중앙, 2=오른쪽
        [SerializeField] private float rushSpeed = 15f;

        [Header("Flying Settings")]
        [SerializeField] private bool destroyOnDistance = true;
        [SerializeField] private float maxDistance = 100f;

        private Rigidbody rb;
        private Vector3 startPosition;
        private bool isMoving = false;

        private void Awake()
        {
            rb = GetComponent<Rigidbody>();
            
            // Rigidbody 설정
            rb.useGravity = false;
            rb.isKinematic = true;  // 물리 충돌은 Collider로만 처리
        }

        private void Start()
        {
            // AutoLaneCalculator 자동 찾기 (할당 안 되어 있으면)
            if (laneCalculator == null)
            {
                laneCalculator = FindObjectOfType<AutoLaneCalculator>();
                
                if (laneCalculator == null)
                {
                    Debug.LogError("[LaneRushObstacle_Auto] AutoLaneCalculator를 찾을 수 없습니다!");
                    return;
                }
            }

            // 레인 위치로 이동
            MoveToLane(laneIndex);
            
            startPosition = transform.position;
            isMoving = true;
        }

        private void Update()
        {
            if (!isMoving) return;

            // 플레이어 방향으로 돌진 (Z축 음수 방향)
            transform.Translate(Vector3.back * rushSpeed * Time.deltaTime, Space.World);

            // 거리 체크해서 자동 삭제
            if (destroyOnDistance)
            {
                float distance = Vector3.Distance(transform.position, startPosition);
                if (distance > maxDistance)
                {
                    Destroy(gameObject);
                }
            }
        }

        /// <summary>
        /// 지정된 레인으로 이동
        /// </summary>
        public void MoveToLane(int newLaneIndex)
        {
            if (laneCalculator == null) return;

            laneIndex = newLaneIndex;
            
            // AutoLaneCalculator에서 레인 위치 가져오기
            float laneX = laneCalculator.GetLanePosition(laneIndex);
            
            // X 위치만 변경 (Y, Z는 유지)
            Vector3 newPos = transform.position;
            newPos.x = laneX;
            transform.position = newPos;

            Debug.Log($"[LaneRushObstacle_Auto] 레인 {laneIndex}로 이동: X = {laneX:F2}");
        }

        /// <summary>
        /// 초기화 (Spawner에서 호출)
        /// </summary>
        public void Initialize(int lane, float speed, AutoLaneCalculator calculator)
        {
            laneCalculator = calculator;
            rushSpeed = speed;
            MoveToLane(lane);
            startPosition = transform.position;
            isMoving = true;
        }
    }
}

