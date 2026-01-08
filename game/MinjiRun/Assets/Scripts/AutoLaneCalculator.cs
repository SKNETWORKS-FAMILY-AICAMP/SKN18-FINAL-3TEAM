using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 트랙 넓이를 자동으로 감지해서 3개 레인의 위치를 계산
    /// </summary>
    public class AutoLaneCalculator : MonoBehaviour
    {
        [Header("Track Reference")]
        [SerializeField] private GameObject trackObject;  // 실제 길(트랙) 오브젝트
        [Tooltip("레일을 배치할 트랙 오브젝트")]

        [Header("Lane Settings")]
        [SerializeField] private int numberOfLanes = 3;  // 레인 개수
        [SerializeField] private float laneMargin = 0.5f;  // 양쪽 여백 (안전 거리)

        [Header("Debug")]
        [SerializeField] private bool showGizmos = true;  // 레인 위치 시각화
        [SerializeField] private Color gizmoColor = Color.green;

        private float trackWidth;
        private float calculatedLaneWidth;
        private float[] lanePositions;

        private void Start()
        {
            CalculateLanePositions();
        }

        /// <summary>
        /// 트랙 넓이를 감지하고 레인 위치 계산
        /// </summary>
        public void CalculateLanePositions()
        {
            if (trackObject == null)
            {
                Debug.LogError("[AutoLaneCalculator] Track Object가 할당되지 않았습니다!");
                return;
            }

            // 트랙의 실제 넓이 계산 (Renderer 기준)
            Renderer trackRenderer = trackObject.GetComponent<Renderer>();
            if (trackRenderer != null)
            {
                trackWidth = trackRenderer.bounds.size.x;
            }
            else
            {
                // Renderer가 없으면 Transform Scale 사용
                trackWidth = trackObject.transform.localScale.x;
            }

            // 여백을 제외한 사용 가능한 넓이
            float usableWidth = trackWidth - (laneMargin * 2);

            // 레인 간격 계산
            calculatedLaneWidth = usableWidth / numberOfLanes;

            // 각 레인의 X 위치 계산
            lanePositions = new float[numberOfLanes];
            
            // 3개 레인인 경우:
            // 왼쪽: -calculatedLaneWidth
            // 중앙: 0
            // 오른쪽: +calculatedLaneWidth
            float startX = -(usableWidth / 2) + (calculatedLaneWidth / 2);
            
            for (int i = 0; i < numberOfLanes; i++)
            {
                lanePositions[i] = startX + (i * calculatedLaneWidth);
            }

            Debug.Log($"[AutoLaneCalculator] 트랙 넓이: {trackWidth:F2}, 레인 넓이: {calculatedLaneWidth:F2}");
            for (int i = 0; i < numberOfLanes; i++)
            {
                Debug.Log($"  레인 {i}: X = {lanePositions[i]:F2}");
            }
        }

        /// <summary>
        /// 특정 레인 인덱스의 X 위치 가져오기
        /// </summary>
        public float GetLanePosition(int laneIndex)
        {
            if (lanePositions == null || lanePositions.Length == 0)
            {
                CalculateLanePositions();
            }

            if (laneIndex < 0 || laneIndex >= numberOfLanes)
            {
                Debug.LogWarning($"[AutoLaneCalculator] 잘못된 레인 인덱스: {laneIndex}");
                return 0f;
            }

            return lanePositions[laneIndex];
        }

        /// <summary>
        /// 계산된 레인 넓이 가져오기
        /// </summary>
        public float GetLaneWidth()
        {
            if (lanePositions == null || lanePositions.Length == 0)
            {
                CalculateLanePositions();
            }

            return calculatedLaneWidth;
        }

        /// <summary>
        /// 레인 위치 시각화 (Scene View에서만 보임)
        /// </summary>
        private void OnDrawGizmos()
        {
            if (!showGizmos || trackObject == null) return;

            // Start()가 호출되기 전이면 미리 계산
            if (lanePositions == null || lanePositions.Length == 0)
            {
                CalculateLanePositions();
            }

            if (lanePositions == null) return;

            Gizmos.color = gizmoColor;

            // 각 레인 위치에 선 그리기
            for (int i = 0; i < lanePositions.Length; i++)
            {
                Vector3 lanePos = transform.position + new Vector3(lanePositions[i], 0, 0);
                
                // 레인 중앙선 그리기 (앞뒤로 길게)
                Vector3 start = lanePos + new Vector3(0, 0, -50);
                Vector3 end = lanePos + new Vector3(0, 0, 50);
                Gizmos.DrawLine(start, end);

                // 레인 번호 표시 (Scene View에서만 보임)
                #if UNITY_EDITOR
                UnityEditor.Handles.Label(lanePos + Vector3.up * 2, $"Lane {i}");
                #endif
            }

            // 트랙 경계선 그리기
            Gizmos.color = Color.red;
            float halfWidth = trackWidth / 2f;
            Vector3 leftEdge = transform.position + new Vector3(-halfWidth, 0, 0);
            Vector3 rightEdge = transform.position + new Vector3(halfWidth, 0, 0);
            
            Gizmos.DrawLine(leftEdge + Vector3.forward * 50, leftEdge - Vector3.forward * 50);
            Gizmos.DrawLine(rightEdge + Vector3.forward * 50, rightEdge - Vector3.forward * 50);
        }

        // 접근자
        public float TrackWidth => trackWidth;
        public int NumberOfLanes => numberOfLanes;
        public float[] LanePositions => lanePositions;
    }
}

