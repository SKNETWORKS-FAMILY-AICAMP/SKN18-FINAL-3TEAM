using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 발사체 자동 생성기
    /// 여러 위치에서 반복적으로 장애물 발사
    /// </summary>
    public class ProjectileSpawner : MonoBehaviour
    {
        [Header("Spawner Settings")]
        [SerializeField] private bool autoSpawn = true;              // 자동 발사 활성화
        [SerializeField] private float spawnInterval = 2f;           // 발사 간격 (초)
        [SerializeField] private float spawnDelay = 0f;              // 시작 지연 시간
        [SerializeField] private int maxSpawnCount = -1;             // 최대 발사 횟수 (-1 = 무제한)

        [Header("Projectile Settings")]
        [SerializeField] private GameObject projectilePrefab;        // 발사체 프리팹
        [SerializeField] private float projectileSpeed = 8f;         // 발사 속도
        [SerializeField] private float projectileLifetime = 5f;      // 생존 시간 (초)

        [Header("Spawn Positions")]
        [SerializeField] private SpawnPoint[] spawnPoints;           // 발사 위치들
        [SerializeField] private bool randomSpawn = true;            // 랜덤 위치에서 발사
        [SerializeField] private bool spawnAllAtOnce = false;        // 모든 위치에서 동시 발사

        [Header("Visual (Optional)")]
        [SerializeField] private bool showGizmos = true;             // Scene 뷰에서 표시

        private float spawnTimer = 0f;
        private int currentSpawnCount = 0;
        private List<GameObject> spawnedProjectiles = new List<GameObject>();
        private Transform playerTransform;

        [System.Serializable]
        public class SpawnPoint
        {
            public Vector3 localPosition;      // 로컬 위치
            public Vector3 direction;          // 발사 방향 (정규화됨)
            [Range(0f, 1f)] public float spawnChance = 1f;  // 발생 확률

            public SpawnPoint(Vector3 pos, Vector3 dir)
            {
                localPosition = pos;
                direction = dir.normalized;
                spawnChance = 1f;
            }
        }

        private void Start()
        {
            // 플레이어 찾기
            GameObject player = GameObject.FindGameObjectWithTag("Player");
            if (player != null)
            {
                playerTransform = player.transform;
            }

            // 기본 발사 위치 설정 (Inspector에서 설정 안했을 경우)
            if (spawnPoints == null || spawnPoints.Length == 0)
            {
                SetupDefaultSpawnPoints();
            }

            // 시작 지연 후 발사 시작
            if (spawnDelay > 0f)
            {
                Invoke(nameof(EnableSpawning), spawnDelay);
            }
        }

        private void Update()
        {
            if (!autoSpawn) return;

            // 최대 발사 횟수 체크
            if (maxSpawnCount >= 0 && currentSpawnCount >= maxSpawnCount)
            {
                autoSpawn = false;
                return;
            }

            spawnTimer += Time.deltaTime;

            if (spawnTimer >= spawnInterval)
            {
                spawnTimer = 0f;
                SpawnProjectiles();
                currentSpawnCount++;
            }

            // 생존 시간 지난 발사체 정리
            CleanupProjectiles();
        }

        /// <summary>
        /// 발사체 생성
        /// </summary>
        private void SpawnProjectiles()
        {
            if (projectilePrefab == null)
            {
                Debug.LogError("[ProjectileSpawner] Projectile prefab is not assigned!");
                return;
            }

            if (spawnPoints == null || spawnPoints.Length == 0)
            {
                Debug.LogError("[ProjectileSpawner] No spawn points available!");
                return;
            }

            if (spawnAllAtOnce)
            {
                // 모든 위치에서 동시 발사
                foreach (SpawnPoint point in spawnPoints)
                {
                    if (Random.value <= point.spawnChance)
                    {
                        SpawnProjectileAtPoint(point);
                    }
                }
            }
            else if (randomSpawn)
            {
                // 랜덤 위치 선택
                SpawnPoint randomPoint = spawnPoints[Random.Range(0, spawnPoints.Length)];
                if (Random.value <= randomPoint.spawnChance)
                {
                    SpawnProjectileAtPoint(randomPoint);
                }
            }
            else
            {
                // 순차적으로 발사
                int index = currentSpawnCount % spawnPoints.Length;
                SpawnProjectileAtPoint(spawnPoints[index]);
            }
        }

        /// <summary>
        /// 특정 위치에서 발사체 생성
        /// </summary>
        private void SpawnProjectileAtPoint(SpawnPoint point)
        {
            // 월드 위치 계산
            Vector3 worldPosition = transform.TransformPoint(point.localPosition);

            // 발사체 생성
            GameObject projectile = Instantiate(projectilePrefab, worldPosition, Quaternion.identity);
            projectile.transform.SetParent(transform);

            // ObstacleController 설정
            ObstacleController controller = projectile.GetComponent<ObstacleController>();
            if (controller != null)
            {
                // Reflection으로 private 필드 설정
                var flyModeField = typeof(ObstacleController).GetField("flyMode",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                var flyDirectionField = typeof(ObstacleController).GetField("flyDirection",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                var flySpeedField = typeof(ObstacleController).GetField("flySpeed",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                var destroyOnDistanceField = typeof(ObstacleController).GetField("destroyOnDistance",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                var maxDistanceField = typeof(ObstacleController).GetField("maxDistance",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

                if (flyModeField != null)
                    flyModeField.SetValue(controller, ObstacleController.FlyMode.Projectile);
                if (flyDirectionField != null)
                    flyDirectionField.SetValue(controller, point.direction);
                if (flySpeedField != null)
                    flySpeedField.SetValue(controller, projectileSpeed);
                if (destroyOnDistanceField != null)
                    destroyOnDistanceField.SetValue(controller, true);
                if (maxDistanceField != null)
                    maxDistanceField.SetValue(controller, projectileSpeed * projectileLifetime);
            }

            spawnedProjectiles.Add(projectile);

            Debug.Log($"[ProjectileSpawner] Projectile spawned at {worldPosition}, direction: {point.direction}");
        }

        /// <summary>
        /// 생존 시간 지난 발사체 정리
        /// </summary>
        private void CleanupProjectiles()
        {
            spawnedProjectiles.RemoveAll(p => p == null);
        }

        /// <summary>
        /// 기본 발사 위치 설정 (좌우 2개)
        /// </summary>
        private void SetupDefaultSpawnPoints()
        {
            spawnPoints = new SpawnPoint[]
            {
                new SpawnPoint(new Vector3(-8f, 1f, 0f), Vector3.right),   // 왼쪽에서 오른쪽으로
                new SpawnPoint(new Vector3(8f, 1f, 0f), Vector3.left),     // 오른쪽에서 왼쪽으로
                new SpawnPoint(new Vector3(-8f, 2f, 0f), new Vector3(1f, -0.3f, 0f)),  // 왼쪽 위에서 아래로
                new SpawnPoint(new Vector3(8f, 2f, 0f), new Vector3(-1f, -0.3f, 0f)),  // 오른쪽 위에서 아래로
            };
        }

        /// <summary>
        /// 발사 활성화
        /// </summary>
        private void EnableSpawning()
        {
            autoSpawn = true;
        }

        /// <summary>
        /// 수동 발사 (테스트용)
        /// </summary>
        public void ManualSpawn()
        {
            SpawnProjectiles();
        }

        /// <summary>
        /// 모든 발사체 제거
        /// </summary>
        public void ClearAllProjectiles()
        {
            foreach (GameObject projectile in spawnedProjectiles)
            {
                if (projectile != null)
                {
                    Destroy(projectile);
                }
            }
            spawnedProjectiles.Clear();
        }

        /// <summary>
        /// 리셋
        /// </summary>
        public void ResetSpawner()
        {
            currentSpawnCount = 0;
            spawnTimer = 0f;
            autoSpawn = true;
            ClearAllProjectiles();
        }

        /// <summary>
        /// Scene 뷰에서 발사 위치 표시
        /// </summary>
        private void OnDrawGizmos()
        {
            if (!showGizmos || spawnPoints == null) return;

            foreach (SpawnPoint point in spawnPoints)
            {
                // 월드 위치 계산
                Vector3 worldPos = transform.TransformPoint(point.localPosition);

                // 발사 위치 표시 (노란색 구)
                Gizmos.color = Color.yellow;
                Gizmos.DrawWireSphere(worldPos, 0.5f);

                // 발사 방향 표시 (빨간색 화살표)
                Gizmos.color = Color.red;
                Gizmos.DrawRay(worldPos, point.direction * 3f);

                // 확률 표시 (구의 크기)
                Gizmos.color = new Color(1f, 1f, 0f, point.spawnChance);
                Gizmos.DrawSphere(worldPos, 0.3f);
            }
        }
    }
}

