using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 트랙의 고정 위치에 장애물을 생성하는 Spawner
    /// 플레이어가 아닌 트랙 위치 기준
    /// </summary>
    public class FixedLaneObstacleSpawner : MonoBehaviour
    {
        [Header("Lane Calculator")]
        [SerializeField] private AutoLaneCalculator laneCalculator;

        [Header("Obstacle Prefab")]
        [SerializeField] private GameObject obstaclePrefab;
        [SerializeField] private float obstacleRushSpeed = 15f;

        [Header("Fixed Spawn Points")]
        [SerializeField] private float[] spawnZPositions;
        [Tooltip("트랙의 Z 위치들 (예: 100, 150, 200, 250)")]
        
        [SerializeField] private SpawnPattern[] spawnPatterns;

        private Transform player;
        private int currentSpawnIndex = 0;
        private List<GameObject> spawnedObstacles = new List<GameObject>();

        [System.Serializable]
        public class SpawnPattern
        {
            public string patternName = "Pattern";
            public int[] lanes;  // 레인 인덱스
            [Range(0f, 1f)]
            public float probability = 0.2f;
        }

        private void Start()
        {
            // Player 찾기
            GameObject playerObj = GameObject.FindGameObjectWithTag("Player");
            if (playerObj != null)
            {
                player = playerObj.transform;
            }

            // AutoLaneCalculator 찾기
            if (laneCalculator == null)
            {
                laneCalculator = FindObjectOfType<AutoLaneCalculator>();
            }

            // 고정 위치가 없으면 기본 값 생성
            if (spawnZPositions == null || spawnZPositions.Length == 0)
            {
                // 기본: 50m마다 생성 (100, 150, 200, 250, ...)
                spawnZPositions = new float[10];
                for (int i = 0; i < 10; i++)
                {
                    spawnZPositions[i] = 100 + (i * 50);
                }
                Debug.LogWarning("[FixedLaneObstacleSpawner] Spawn Z Positions가 설정되지 않아 기본값 사용");
            }
        }

        private void Update()
        {
            if (player == null) return;

            // 플레이어가 다음 생성 지점에 가까워지면 생성
            CheckAndSpawnNextObstacle();
        }

        /// <summary>
        /// 플레이어가 다음 생성 지점에 접근하면 생성
        /// </summary>
        private void CheckAndSpawnNextObstacle()
        {
            if (currentSpawnIndex >= spawnZPositions.Length)
            {
                // 모든 장애물 생성 완료
                return;
            }

            float nextSpawnZ = spawnZPositions[currentSpawnIndex];
            float distanceToSpawn = nextSpawnZ - player.position.z;

            // 플레이어가 생성 지점 50m 전까지 왔으면 생성
            if (distanceToSpawn <= 50f && distanceToSpawn > 0f)
            {
                SpawnObstaclesAtPosition(nextSpawnZ);
                currentSpawnIndex++;
            }
        }

        /// <summary>
        /// 특정 Z 위치에 장애물 생성
        /// </summary>
        private void SpawnObstaclesAtPosition(float zPosition)
        {
            if (spawnPatterns == null || spawnPatterns.Length == 0)
            {
                Debug.LogError("[FixedLaneObstacleSpawner] Spawn Patterns가 설정되지 않았습니다!");
                return;
            }

            // 패턴 선택
            SpawnPattern selectedPattern = SelectPattern();

            if (selectedPattern != null && selectedPattern.lanes != null)
            {
                foreach (int laneIndex in selectedPattern.lanes)
                {
                    SpawnObstacleAtLane(laneIndex, zPosition);
                }

                Debug.Log($"[FixedLaneObstacleSpawner] Z={zPosition}에 {selectedPattern.patternName} 생성");
            }
        }

        /// <summary>
        /// 특정 레인과 Z 위치에 장애물 생성
        /// </summary>
        private void SpawnObstacleAtLane(int laneIndex, float zPosition)
        {
            if (laneCalculator == null) return;

            float laneX = laneCalculator.GetLanePosition(laneIndex);

            // 고정 위치에 생성!
            Vector3 spawnPosition = new Vector3(
                laneX,
                1f,
                zPosition  // ← 고정된 Z 위치!
            );

            GameObject obstacle = Instantiate(obstaclePrefab, spawnPosition, obstaclePrefab.transform.rotation);
            obstacle.transform.SetParent(transform);

            // LaneRushObstacle_Auto 초기화
            LaneRushObstacle_Auto rushObstacle = obstacle.GetComponent<LaneRushObstacle_Auto>();
            if (rushObstacle != null)
            {
                rushObstacle.Initialize(laneIndex, obstacleRushSpeed, laneCalculator);
            }

            spawnedObstacles.Add(obstacle);
        }

        /// <summary>
        /// 확률에 따라 패턴 선택
        /// </summary>
        private SpawnPattern SelectPattern()
        {
            float totalProbability = 0f;
            foreach (var pattern in spawnPatterns)
            {
                totalProbability += pattern.probability;
            }

            float randomValue = Random.Range(0f, totalProbability);
            float currentProbability = 0f;

            foreach (var pattern in spawnPatterns)
            {
                currentProbability += pattern.probability;
                if (randomValue <= currentProbability)
                {
                    return pattern;
                }
            }

            return spawnPatterns[0];
        }

        /// <summary>
        /// 게임 재시작 시 리셋
        /// </summary>
        public void ResetSpawner()
        {
            currentSpawnIndex = 0;

            foreach (GameObject obstacle in spawnedObstacles)
            {
                if (obstacle != null)
                {
                    Destroy(obstacle);
                }
            }

            spawnedObstacles.Clear();
        }

        /// <summary>
        /// 디버그용: 생성 지점 시각화
        /// </summary>
        private void OnDrawGizmos()
        {
            if (spawnZPositions == null || spawnZPositions.Length == 0) return;

            Gizmos.color = Color.yellow;

            foreach (float zPos in spawnZPositions)
            {
                Vector3 position = new Vector3(0, 1, zPos);
                
                // 생성 지점에 선 그리기
                Gizmos.DrawLine(position + Vector3.left * 10, position + Vector3.right * 10);
                
                #if UNITY_EDITOR
                UnityEditor.Handles.Label(position + Vector3.up * 2, $"Spawn Z={zPos}");
                #endif
            }
        }
    }
}

