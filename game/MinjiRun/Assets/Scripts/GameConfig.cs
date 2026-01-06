using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 게임 전역 설정
    /// </summary>
    [CreateAssetMenu(fileName = "GameConfig", menuName = "minji_run/Game Config")]
    public class GameConfig : ScriptableObject
    {
        [Header("Player Settings")]
        public float moveSpeed = 5f;                // 이동 속도
        public float jumpForce = 8f;                // 점프 힘
        public float gravity = 20f;                 // 중력
        public float rotationSpeed = 10f;           // 회전 속도

        [Header("Quiz Settings")]
        public float quizTimeLimit = 30f;           // 퀴즈 제한 시간
        public float quizInterval = 50f;            // 퀴즈 출제 간격 (거리)

        [Header("Track Settings")]
        public float segmentLength = 50f;           // 세그먼트 길이
        public float segmentWidth = 10f;            // 세그먼트 폭

        [Header("Camera Settings")]
        public Vector3 cameraOffset = new Vector3(0f, 5f, -10f);  // 카메라 오프셋
        public float cameraSmoothSpeed = 5f;        // 카메라 따라가기 속도

        [Header("Performance (WebGL)")]
        public int objectPoolSize = 20;             // 오브젝트 풀 크기
        public bool enableShadows = false;          // 그림자 활성화 (WebGL에서는 비추천)
        public int targetFrameRate = 60;            // 목표 프레임레이트
    }
}
