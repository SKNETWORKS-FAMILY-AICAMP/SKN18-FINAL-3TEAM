using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 레인 장애물 자동 생성 시스템
    /// 주기적으로 1~3개 레인에 장애물 생성
    /// </summary>
    public class LaneObstacleSpawner : MonoBehaviour
    {
        [Header("Spawner Settings")]
        [SerializeField] private bool autoSpawn = true;                  // 자동 생성 활성화
        [SerializeField] private bool usePlayerPosition = false;         // 플레이어 위치 기반 생성 (false = 고정 위치)
        [SerializeField] private float spawnInterval = 2.5f;             // 생성 간격 (초)
        [SerializeField] private float spawnDistance = 50f;              // 생성 거리 (앞쪽)
        [SerializeField] private float spawnHeight = 1f;                 // 생성 높이
        [SerializeField] private float triggerDistance = 30f;            // 플레이어가 이 거리 안에 들어오면 활성화
        [SerializeField] [Range(0f, 1f)] private float spawnProbability = 0.75f;  // 생성 확률 (0~1)

        [Header("Obstacle Prefab")]
        [SerializeField] private GameObject obstaclePrefab;              // 장애물 프리팹
        [SerializeField] private float obstacleRushSpeed = 15f;          // 장애물 돌진 속도

        [Header("Lane Settings")]
        [SerializeField] private float laneWidth = 3f;                   // 레인 간격
        [SerializeField] private int minLanes = 1;                       // 최소 레인 개수 (동시 생성)
        [SerializeField] private int maxLanes = 2;                       // 최대 레인 개수 (동시 생성)

        [Header("Pattern Settings")]
        [SerializeField] private bool usePatterns = true;                // 패턴 사용 여부
        [SerializeField] private SpawnPattern[] spawnPatterns;           // 생성 패턴들

        private float spawnTimer = 0f;
        private Transform playerTransform;
        private List<GameObject> spawnedObstacles = new List<GameObject>();
        private bool hasTriggered = false;  // 이미 활성화되었는지 확인

        [System.Serializable]
        public class SpawnPattern
        {
            public string patternName;                                   // 패턴 이름
            public int[] lanes;                                          // 생성할 레인들 (0=왼쪽, 1=중앙, 2=오른쪽)
            [Range(0f, 1f)] public float probability = 0.33f;            // 발생 확률
        }

        private void Start()
        {
            Debug.Log("[LaneObstacleSpawner] Starting...");
            
            // 플레이어 찾기
            GameObject player = GameObject.FindGameObjectWithTag("Player");
            if (player != null)
            {
                playerTransform = player.transform;
                Debug.Log($"[LaneObstacleSpawner] Player found at position: {playerTransform.position}");
            }
            else
            {
                Debug.LogWarning("[LaneObstacleSpawner] Player not found! Make sure Player has 'Player' tag.");
            }

            // Obstacle Prefab 확인
            if (obstaclePrefab == null)
            {
                Debug.LogError("[LaneObstacleSpawner] Obstacle Prefab is NOT assigned in Inspector!");
            }
            else
            {
                Debug.Log($"[LaneObstacleSpawner] Obstacle Prefab assigned: {obstaclePrefab.name}");
            }

            // Auto Spawn 확인
            Debug.Log($"[LaneObstacleSpawner] Auto Spawn: {autoSpawn}, Spawn Interval: {spawnInterval}");

            // 기본 패턴 설정 (Inspector에서 설정 안했을 경우)
            if (spawnPatterns == null || spawnPatterns.Length == 0)
            {
                SetupDefaultPatterns();
            }
        }

        private void Update()
        {
            if (!autoSpawn) return;

            // 플레이어 위치 기반 모드일 때만 플레이어 필요
            if (usePlayerPosition)
            {
                // 플레이어를 못 찾았으면 다시 찾기
                if (playerTransform == null)
                {
                    GameObject player = GameObject.FindGameObjectWithTag("Player");
                    if (player != null)
                    {
                        playerTransform = player.transform;
                        Debug.Log("[LaneObstacleSpawner] Player found!");
                    }
                    else
                    {
                        return; // 여전히 못 찾으면 리턴
                    }
                }
            }

            // 타이머 업데이트 및 생성
            spawnTimer += Time.deltaTime;

            if (spawnTimer >= spawnInterval)
            {
                spawnTimer = 0f;
                
                // 확률 체크: 랜덤으로 생성 여부 결정
                float randomValue = Random.value;
                Debug.Log($"[LaneObstacleSpawner] {gameObject.name} timer reached! Random: {randomValue:F2}, Probability: {spawnProbability:F2}");
                
                if (randomValue < spawnProbability)
                {
                    Debug.Log($"[LaneObstacleSpawner] {gameObject.name} WILL SPAWN (passed probability check)");
                    SpawnObstacles();
                }
                else
                {
                    Debug.Log($"[LaneObstacleSpawner] {gameObject.name} SKIPPED (failed probability check)");
                }
            }

            // 뒤로 지나간 장애물 정리
            CleanupObstacles();
        }

        /// <summary>
        /// 장애물 생성
        /// </summary>
        private void SpawnObstacles()
        {
            Debug.Log("[LaneObstacleSpawner] SpawnObstacles() called!");
            
            if (obstaclePrefab == null)
            {
                Debug.LogError("[LaneObstacleSpawner] ❌ Obstacle prefab is not assigned!");
                return;
            }

            if (playerTransform == null)
            {
                Debug.LogError("[LaneObstacleSpawner] ❌ Player transform is null!");
                return;
            }

            int[] lanesToSpawn;

            if (usePatterns && spawnPatterns != null && spawnPatterns.Length > 0)
            {
                // 패턴 사용
                lanesToSpawn = SelectPatternLanes();
                Debug.Log($"[LaneObstacleSpawner] Using pattern mode, lanes: {string.Join(", ", lanesToSpawn)}");
            }
            else
            {
                // 랜덤 레인 선택
                lanesToSpawn = SelectRandomLanes();
                Debug.Log($"[LaneObstacleSpawner] Using random mode, lanes: {string.Join(", ", lanesToSpawn)}");
            }

            // 각 레인에 장애물 생성
            foreach (int laneIndex in lanesToSpawn)
            {
                SpawnObstacleAtLane(laneIndex);
            }
            
            Debug.Log($"[LaneObstacleSpawner] ✅ Spawned {lanesToSpawn.Length} obstacles");
        }

        /// <summary>
        /// 패턴에 따른 레인 선택
        /// </summary>
        private int[] SelectPatternLanes()
        {
            // 확률에 따라 패턴 선택
            float random = Random.value;
            float cumulativeProbability = 0f;

            foreach (SpawnPattern pattern in spawnPatterns)
            {
                cumulativeProbability += pattern.probability;
                if (random <= cumulativeProbability)
                {
                    return pattern.lanes;
                }
            }

            // 기본값: 첫 번째 패턴
            return spawnPatterns[0].lanes;
        }

        /// <summary>
        /// 랜덤 레인 선택
        /// </summary>
        private int[] SelectRandomLanes()
        {
            int laneCount = Random.Range(minLanes, maxLanes + 1);
            List<int> availableLanes = new List<int> { 0, 1, 2 };
            List<int> selectedLanes = new List<int>();

            for (int i = 0; i < laneCount; i++)
            {
                if (availableLanes.Count == 0) break;

                int randomIndex = Random.Range(0, availableLanes.Count);
                selectedLanes.Add(availableLanes[randomIndex]);
                availableLanes.RemoveAt(randomIndex);
            }

            return selectedLanes.ToArray();
        }

        /// <summary>
        /// 특정 레인에 장애물 생성
        /// </summary>
        private void SpawnObstacleAtLane(int laneIndex)
        {
            if (playerTransform == null && usePlayerPosition)
            {
                Debug.LogWarning("[LaneObstacleSpawner] ⚠️ Player not found!");
                return;
            }

            // 생성 위치 계산
            float laneX = (laneIndex - 1) * laneWidth;  // -laneWidth, 0, +laneWidth
            
            Vector3 spawnPosition;
            if (usePlayerPosition)
            {
                // 플레이어 위치 기반 (기존 방식)
                spawnPosition = new Vector3(
                    laneX,
                    spawnHeight,
                    playerTransform.position.z + spawnDistance
                );
            }
            else
            {
                // 고정 위치 기반 (새로운 방식)
                spawnPosition = new Vector3(
                    laneX,  // 레인은 항상 중앙 기준 (-3, 0, +3)
                    transform.position.y + spawnHeight,  // Spawner Y + 높이 오프셋
                    transform.position.z  // Spawner Z 위치에서 생성
                );
            }

            Debug.Log($"[LaneObstacleSpawner] Creating obstacle at Lane {laneIndex}, Position: {spawnPosition}");

            // 장애물 생성
            GameObject obstacle = Instantiate(obstaclePrefab, spawnPosition, Quaternion.identity);
            obstacle.name = $"ObstacleRush_Lane{laneIndex}";
            obstacle.transform.SetParent(transform);

            Debug.Log($"[LaneObstacleSpawner] ✅ Obstacle instantiated: {obstacle.name}");

            // ObstacleController 설정
            ObstacleController controller = obstacle.GetComponent<ObstacleController>();
            if (controller != null)
            {
                // Public 메서드를 사용하여 LaneRush 모드 설정
                controller.SetupLaneRush(laneIndex, laneWidth, obstacleRushSpeed);
                Debug.Log($"[LaneObstacleSpawner] ✅ ObstacleController setup complete for lane {laneIndex}");
            }
            else
            {
                Debug.LogError($"[LaneObstacleSpawner] ❌ ObstacleController NOT FOUND on {obstaclePrefab.name}!");
            }

            spawnedObstacles.Add(obstacle);
        }

        /// <summary>
        /// 뒤로 지나간 장애물 정리
        /// </summary>
        private void CleanupObstacles()
        {
            for (int i = spawnedObstacles.Count - 1; i >= 0; i--)
            {
                if (spawnedObstacles[i] == null)
                {
                    spawnedObstacles.RemoveAt(i);
                }
                else if (playerTransform != null && spawnedObstacles[i].transform.position.z < playerTransform.position.z - 20f)
                {
                    Destroy(spawnedObstacles[i]);
                    spawnedObstacles.RemoveAt(i);
                }
                else if (playerTransform == null && Vector3.Distance(spawnedObstacles[i].transform.position, transform.position) > 100f)
                {
                    // 플레이어 없으면 Spawner 기준으로 100m 이상 멀어지면 삭제
                    Destroy(spawnedObstacles[i]);
                    spawnedObstacles.RemoveAt(i);
                }
            }
        }

        /// <summary>
        /// 기본 패턴 설정
        /// </summary>
        private void SetupDefaultPatterns()
        {
            spawnPatterns = new SpawnPattern[]
            {
                new SpawnPattern { patternName = "Single_Left", lanes = new int[] { 0 }, probability = 0.2f },
                new SpawnPattern { patternName = "Single_Center", lanes = new int[] { 1 }, probability = 0.2f },
                new SpawnPattern { patternName = "Single_Right", lanes = new int[] { 2 }, probability = 0.2f },
                new SpawnPattern { patternName = "Double_LeftCenter", lanes = new int[] { 0, 1 }, probability = 0.15f },
                new SpawnPattern { patternName = "Double_CenterRight", lanes = new int[] { 1, 2 }, probability = 0.15f },
                new SpawnPattern { patternName = "Double_LeftRight", lanes = new int[] { 0, 2 }, probability = 0.1f },
            };
        }

        /// <summary>
        /// 수동으로 장애물 생성 (테스트용)
        /// </summary>
        public void ManualSpawn()
        {
            SpawnObstacles();
        }

        /// <summary>
        /// 모든 장애물 제거
        /// </summary>
        public void ClearAllObstacles()
        {
            foreach (GameObject obstacle in spawnedObstacles)
            {
                if (obstacle != null)
                {
                    Destroy(obstacle);
                }
            }
            spawnedObstacles.Clear();
        }
    }
}
