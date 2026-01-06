using UnityEngine;
using System;

namespace minji_run
{
    /// <summary>
    /// 게임 타이머 관리자 (싱글톤)
    /// 100초 제한 시간, 정답 +5초, 오답 -5초
    /// </summary>
    public class GameTimerManager : MonoBehaviour
    {
        public static GameTimerManager Instance { get; private set; }

        [Header("Timer Settings")]
        [SerializeField] private float startTime = 100f;  // 시작 시간 (기본 100초)
        [SerializeField] private float bonusTime = 5f;    // 정답 시 추가 시간
        [SerializeField] private float penaltyTime = 5f;  // 오답 시 감소 시간

        [Header("Current Timer")]
        [SerializeField] private float currentTime;
        [SerializeField] private bool isTimerRunning = false;

        // 이벤트
        public event Action<float> OnTimerUpdated;     // 타이머 업데이트 (남은 시간)
        public event Action OnTimerExpired;            // 타이머 종료

        private void Awake()
        {
            // 싱글톤 설정
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
        }

        private void Update()
        {
            // 타이머 실행 중일 때만 감소
            if (isTimerRunning && currentTime > 0)
            {
                currentTime -= Time.deltaTime;
                OnTimerUpdated?.Invoke(currentTime);

                // 시간 종료
                if (currentTime <= 0)
                {
                    currentTime = 0;
                    isTimerRunning = false;
                    OnTimerExpired?.Invoke();
                    Debug.Log("[GameTimer] Time expired!");
                }
            }
        }

        /// <summary>
        /// 타이머 시작
        /// </summary>
        public void StartTimer()
        {
            currentTime = startTime;
            isTimerRunning = true;
            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log($"[GameTimer] Timer started: {startTime} seconds");
        }

        /// <summary>
        /// 타이머 정지
        /// </summary>
        public void StopTimer()
        {
            isTimerRunning = false;
            Debug.Log("[GameTimer] Timer stopped");
        }

        /// <summary>
        /// 타이머 재개
        /// </summary>
        public void ResumeTimer()
        {
            isTimerRunning = true;
            Debug.Log("[GameTimer] Timer resumed");
        }

        /// <summary>
        /// 타이머 리셋
        /// </summary>
        public void ResetTimer()
        {
            currentTime = startTime;
            isTimerRunning = false;
            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log("[GameTimer] Timer reset");
        }

        /// <summary>
        /// 보너스 시간 추가 (정답 시)
        /// </summary>
        public void AddBonusTime()
        {
            currentTime += bonusTime;
            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log($"[GameTimer] Bonus time added: +{bonusTime}s (Total: {currentTime:F1}s)");
        }

        /// <summary>
        /// 페널티 시간 감소 (오답 시)
        /// </summary>
        public void ApplyPenalty()
        {
            currentTime -= penaltyTime;
            if (currentTime < 0)
                currentTime = 0;

            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log($"[GameTimer] Penalty applied: -{penaltyTime}s (Total: {currentTime:F1}s)");

            // 페널티로 시간이 0이 되면 게임 오버
            if (currentTime <= 0)
            {
                isTimerRunning = false;
                OnTimerExpired?.Invoke();
            }
        }

        /// <summary>
        /// 특정 시간 추가
        /// </summary>
        public void AddTime(float seconds)
        {
            currentTime += seconds;
            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log($"[GameTimer] Time added: +{seconds}s (Total: {currentTime:F1}s)");
        }

        /// <summary>
        /// 특정 시간 감소
        /// </summary>
        public void SubtractTime(float seconds)
        {
            currentTime -= seconds;
            if (currentTime < 0)
                currentTime = 0;

            OnTimerUpdated?.Invoke(currentTime);
            Debug.Log($"[GameTimer] Time subtracted: -{seconds}s (Total: {currentTime:F1}s)");

            if (currentTime <= 0)
            {
                isTimerRunning = false;
                OnTimerExpired?.Invoke();
            }
        }

        // 접근자
        public float CurrentTime => currentTime;
        public float StartTime => startTime;
        public bool IsTimerRunning => isTimerRunning;
        public float TimeRemainingPercent => currentTime / startTime;
    }
}
