using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 반복 발사 장애물
    /// 배치한 위치에서 일정 간격으로 복제본을 발사
    /// </summary>
    public class RepeatingProjectile : MonoBehaviour
    {
        [Header("Repeat Settings")]
        [SerializeField] private bool enableRepeat = true;           // 반복 발사 활성화
        [SerializeField] private float repeatInterval = 2f;          // 반복 간격 (초)
        [SerializeField] private float startDelay = 0f;              // 시작 지연
        [SerializeField] private int maxRepeats = -1;                // 최대 반복 횟수 (-1 = 무제한)
        [SerializeField] private float projectileLifetime = 5f;      // 발사체 생존 시간

        private Vector3 startPosition;
        private int repeatCount = 0;
        private float repeatTimer = 0f;
        private ObstacleController originalController;
        private GameObject templateObject;

        private void Start()
        {
            // 시작 위치 저장
            startPosition = transform.position;

            // ObstacleController 가져오기
            originalController = GetComponent<ObstacleController>();

            // 템플릿 오브젝트 생성 (원본은 숨김)
            if (enableRepeat)
            {
                // 첫 발사를 위해 즉시 복제
                if (startDelay > 0f)
                {
                    Invoke(nameof(StartRepeating), startDelay);
                }
                else
                {
                    StartRepeating();
                }

                // 원본은 렌더링 끄기 (발사기 역할만)
                MeshRenderer renderer = GetComponent<MeshRenderer>();
                if (renderer != null)
                    renderer.enabled = false;

                // 자식 모델도 끄기
                foreach (MeshRenderer childRenderer in GetComponentsInChildren<MeshRenderer>())
                {
                    childRenderer.enabled = false;
                }

                // 원본 콜라이더 끄기
                Collider col = GetComponent<Collider>();
                if (col != null)
                    col.enabled = false;

                // 원본 ObstacleController 끄기
                if (originalController != null)
                    originalController.enabled = false;
            }
        }

        private void Update()
        {
            if (!enableRepeat) return;

            // 최대 반복 횟수 체크
            if (maxRepeats >= 0 && repeatCount >= maxRepeats)
            {
                return;
            }

            repeatTimer += Time.deltaTime;

            if (repeatTimer >= repeatInterval)
            {
                repeatTimer = 0f;
                SpawnProjectile();
                repeatCount++;
            }
        }

        /// <summary>
        /// 반복 시작
        /// </summary>
        private void StartRepeating()
        {
            // 첫 발사
            SpawnProjectile();
        }

        /// <summary>
        /// 발사체 생성
        /// </summary>
        private void SpawnProjectile()
        {
            // 원본을 복제
            GameObject projectile = Instantiate(gameObject, startPosition, transform.rotation);
            projectile.transform.SetParent(transform.parent);

            // 복제본에서 RepeatingProjectile 제거 (반복 안 하게)
            RepeatingProjectile repeater = projectile.GetComponent<RepeatingProjectile>();
            if (repeater != null)
            {
                Destroy(repeater);
            }

            // 렌더링 다시 켜기
            MeshRenderer renderer = projectile.GetComponent<MeshRenderer>();
            if (renderer != null)
                renderer.enabled = true;

            foreach (MeshRenderer childRenderer in projectile.GetComponentsInChildren<MeshRenderer>())
            {
                childRenderer.enabled = true;
            }

            // 콜라이더 켜기
            Collider col = projectile.GetComponent<Collider>();
            if (col != null)
                col.enabled = true;

            // ObstacleController 켜기
            ObstacleController controller = projectile.GetComponent<ObstacleController>();
            if (controller != null)
            {
                controller.enabled = true;
            }

            // 일정 시간 후 자동 삭제
            Destroy(projectile, projectileLifetime);

            Debug.Log($"[RepeatingProjectile] Projectile spawned at {startPosition}");
        }

        /// <summary>
        /// 리셋
        /// </summary>
        public void ResetRepeater()
        {
            repeatCount = 0;
            repeatTimer = 0f;
        }
    }
}

