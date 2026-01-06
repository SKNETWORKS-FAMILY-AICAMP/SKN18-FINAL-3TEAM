using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 트랙 세그먼트 관리자 (수동 맵 제작 방식)
    /// </summary>
    public class SegmentManager : MonoBehaviour
    {
        public static SegmentManager Instance { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
        }

    }
}
