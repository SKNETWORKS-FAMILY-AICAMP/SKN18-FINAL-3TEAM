using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// AutoLaneCalculator를 사용하는 자동 장애물 생성기
    /// 트랙 넓이에 맞춰 자동으로 레인 배치
    /// </summary>
    public class AutoLaneObstacleSpawner : MonoBehaviour
    {
        [Header("Lane Calculator")]
        [SerializeField] private AutoLaneCalculator laneCalculator;
        [Tooltip("레인 위치를 계산할 AutoLaneCalculator")]

        [Header("Spawner Settings")]
        [SerializeField] private bool autoSpawn = true;
        [SerializeField] private float spawnInterval = 3f;  // 생성 간격 (초)
        [SerializeField] private float spawnDistance = 50f;  // 플레이어 앞 거리
        [SerializeField] private float spawnHeight = 1f;

        [Header("Obstacle Prefab")]
        [SerializeField] private GameObject obstaclePrefab;
        [SerializeField] private float obstacleRushSpeed = 15f;

        [Header("Pattern Settings")]
        [SerializeField] private bool usePatterns = true;
        [SerializeField] private SpawnPattern[] spawnPatterns;

        private Transform player;
        private float nextSpawnTime;
        private List<GameObject> activeObstacles = new List<GameObject>();

        [System.Serializable]
        public class SpawnPattern
        {
            public string patternName = "Pattern";
            public int[] lanes;  // 어느 레인에 생성할지 (0, 1, 2)
            [Range(0f, 1f)]
            public float probability = 0.2f;  // 확률
        }

        private void Start()
        {
            // Player 찾기
            GameObject playerObj = GameObject.FindGameObjectWithTag("Player");
            if (playerObj != null)
            {
                player = playerObj.transform;
            }
            else
            {
                Debug.LogError("[AutoLaneObstacleSpawner] Player not found!");
            }

            // AutoLaneCalculator 자동 찾기
            if (laneCalculator == null)
            {
                laneCalculator = FindObjectOfType<AutoLaneCalculator>();
                
                if (laneCalculator == null)
                {
                    Debug.LogError("[AutoLaneObstacleSpawner] AutoLaneCalculator를 찾을 수 없습니다!");
                    autoSpawn = false;
                    return;
                }
            }

            // Prefab 검증
            if (obstaclePrefab == null)
            {
                Debug.LogError("[AutoLaneObstacleSpawner] Obstacle Prefab이 할당되지 않았습니다!");
                autoSpawn = false;
                return;
            }

            // 첫 생성 시간 설정
            nextSpawnTime = Time.time + spawnInterval;
        }

        private void Update()
        {
            if (!autoSpawn || player == null) return;

            // 생성 간격마다 장애물 생성
            if (Time.time >= nextSpawnTime)
            {
                SpawnObstacles();
                nextSpawnTime = Time.time + spawnInterval;
            }

            // 멀리 간 장애물 제거
            CleanupObstacles();
        }

        /// <summary>
        /// 패턴에 따라 장애물 생성
        /// </summary>
        private void SpawnObstacles()
        {
            if (usePatterns && spawnPatterns != null && spawnPatterns.Length > 0)
            {
                // 패턴 중에서 확률에 따라 선택
                SpawnPattern selectedPattern = SelectPattern();
                
                if (selectedPattern != null && selectedPattern.lanes != null)
                {
                    // 선택된 패턴의 레인들에 장애물 생성
                    foreach (int laneIndex in selectedPattern.lanes)
                    {
                        SpawnObstacleAtLane(laneIndex);
                    }
                    
                    Debug.Log($"[AutoLaneObstacleSpawner] 패턴 생성: {selectedPattern.patternName}, 레인: {string.Join(", ", selectedPattern.lanes)}");
                }
            }
            else
            {
                // 패턴 없이 랜덤 레인에 생성
                int randomLane = Random.Range(0, laneCalculator.NumberOfLanes);
                SpawnObstacleAtLane(randomLane);
            }
        }

        /// <summary>
        /// 특정 레인에 장애물 생성
        /// </summary>
        private void SpawnObstacleAtLane(int laneIndex)
        {
            if (player == null || laneCalculator == null) return;

            // 레인의 X 위치 가져오기 (자동 계산됨!)
            float laneX = laneCalculator.GetLanePosition(laneIndex);

            // 플레이어 앞쪽에 생성 위치 계산
            Vector3 spawnPosition = new Vector3(
                laneX,  // ← 자동으로 계산된 레인 위치!
                spawnHeight,
                player.position.z + spawnDistance
            );

            // 장애물 생성 (Prefab의 원래 Rotation 사용)
            GameObject obstacle = Instantiate(obstaclePrefab, spawnPosition, obstaclePrefab.transform.rotation);
            obstacle.transform.SetParent(transform);  // Spawner의 자식으로 설정

            // LaneRushObstacle_Auto 컴포넌트 초기화
            LaneRushObstacle_Auto rushObstacle = obstacle.GetComponent<LaneRushObstacle_Auto>();
            if (rushObstacle != null)
            {
                rushObstacle.Initialize(laneIndex, obstacleRushSpeed, laneCalculator);
            }
            else
            {
                Debug.LogWarning("[AutoLaneObstacleSpawner] Obstacle에 LaneRushObstacle_Auto가 없습니다!");
            }

            // 활성 장애물 리스트에 추가
            activeObstacles.Add(obstacle);
        }

        /// <summary>
        /// 확률에 따라 패턴 선택
        /// </summary>
        private SpawnPattern SelectPattern()
        {
            if (spawnPatterns == null || spawnPatterns.Length == 0)
                return null;

            // 확률 합계 계산
            float totalProbability = 0f;
            foreach (var pattern in spawnPatterns)
            {
                totalProbability += pattern.probability;
            }

            // 랜덤 값 생성
            float randomValue = Random.Range(0f, totalProbability);

            // 확률에 따라 패턴 선택
            float currentProbability = 0f;
            foreach (var pattern in spawnPatterns)
            {
                currentProbability += pattern.probability;
                if (randomValue <= currentProbability)
                {
                    return pattern;
                }
            }

            // 기본적으로 첫 번째 패턴 반환
            return spawnPatterns[0];
        }

        /// <summary>
        /// 플레이어 뒤로 지나간 장애물 제거
        /// </summary>
        private void CleanupObstacles()
        {
            if (player == null) return;

            // 뒤로 지나간 장애물 찾아서 제거
            for (int i = activeObstacles.Count - 1; i >= 0; i--)
            {
                if (activeObstacles[i] == null)
                {
                    activeObstacles.RemoveAt(i);
                }
                else if (activeObstacles[i].transform.position.z < player.position.z - 20f)
                {
                    Destroy(activeObstacles[i]);
                    activeObstacles.RemoveAt(i);
                }
            }
        }

        /// <summary>
        /// 자동 생성 시작/정지
        /// </summary>
        public void SetAutoSpawn(bool enabled)
        {
            autoSpawn = enabled;
            
            if (enabled)
            {
                nextSpawnTime = Time.time + spawnInterval;
            }
        }

        /// <summary>
        /// 모든 장애물 제거
        /// </summary>
        public void ClearAllObstacles()
        {
            foreach (GameObject obstacle in activeObstacles)
            {
                if (obstacle != null)
                {
                    Destroy(obstacle);
                }
            }
            
            activeObstacles.Clear();
        }

        private void OnDestroy()
        {
            ClearAllObstacles();
        }
    }
}

