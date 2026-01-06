using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 트랙 세그먼트
    /// 재사용 가능한 코스 조각
    /// </summary>
    public class TrackSegment : MonoBehaviour
    {
        [Header("Segment Info")]
        [SerializeField] private float segmentLength = 50f;
        [SerializeField] private Transform startPoint;  // 세그먼트 시작점
        [SerializeField] private Transform endPoint;    // 세그먼트 끝점

        [Header("Obstacles")]
        [SerializeField] private Transform obstacleRoot;  // 장애물들의 부모 오브젝트
        private List<GameObject> obstacles = new List<GameObject>();

        /// <summary>
        /// 세그먼트 초기화
        /// </summary>
        public void Initialize(Vector3 position)
        {
            transform.position = position;

            // 장애물 수집
            CollectObstacles();
        }

        /// <summary>
        /// 장애물 수집
        /// </summary>
        private void CollectObstacles()
        {
            obstacles.Clear();

            if (obstacleRoot != null)
            {
                foreach (Transform child in obstacleRoot)
                {
                    obstacles.Add(child.gameObject);
                }
            }
        }

        /// <summary>
        /// 장애물 모두 제거
        /// </summary>
        public void ClearObstacles()
        {
            foreach (GameObject obstacle in obstacles)
            {
                if (obstacle != null)
                    Destroy(obstacle);
            }
            obstacles.Clear();
        }

        /// <summary>
        /// 세그먼트 재활용
        /// </summary>
        public void Recycle()
        {
            ClearObstacles();
            gameObject.SetActive(false);
        }

        /// <summary>
        /// 세그먼트 활성화
        /// </summary>
        public void Activate(Vector3 position)
        {
            transform.position = position;
            gameObject.SetActive(true);
        }

        // 접근자
        public float Length => segmentLength;
        public Vector3 StartPosition => startPoint != null ? startPoint.position : transform.position;
        public Vector3 EndPosition => endPoint != null ? endPoint.position : transform.position + Vector3.forward * segmentLength;
    }
}
