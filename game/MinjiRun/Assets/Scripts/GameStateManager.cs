using UnityEngine;
using System;

namespace minji_run
{
    /// <summary>
    /// 게임 상태 전환 관리자 (싱글톤)
    /// Running ↔ Quiz ↔ Result ↔ GameOver 상태 관리
    /// </summary>
    public class GameStateManager : MonoBehaviour
    {
        public static GameStateManager Instance { get; private set; }

        [Header("References")]
        [SerializeField] private GameConfig gameConfig;
        [SerializeField] private Transform player;  // 플레이어 Transform
        [SerializeField] private TrackSegment startTrackSegment;  // 시작 트랙 세그먼트

        [Header("Current State")]
        [SerializeField] private GameState currentState = GameState.Running;

        // 게임 통계
        private GameStats gameStats = new GameStats();

        // 이벤트
        public event Action<GameState, GameState> OnStateChanged;  // 상태 변경 이벤트 (이전 상태, 새 상태)
        public event Action<GameStats> OnStatsUpdated;             // 통계 업데이트 이벤트

        private void Awake()
        {
            // 싱글톤 설정
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;

            // 씬 전환 시에도 유지
            // DontDestroyOnLoad(gameObject);
        }

        private void Start()
        {
            InitializeGame();
        }

        private void Update()
        {
            // Running 상태일 때만 플레이 시간 증가
            if (currentState == GameState.Running)
            {
                gameStats.playTime += Time.deltaTime;
            }
        }

        /// <summary>
        /// 게임 초기화
        /// </summary>
        private void InitializeGame()
        {
            gameStats.Reset();

            // 플레이어를 시작 위치로 이동
            MovePlayerToStart();

            // UI 업데이트 (거리 0으로 표시)
            OnStatsUpdated?.Invoke(gameStats);

            ChangeState(GameState.Running);

            // 게임 타이머 시작
            if (GameTimerManager.Instance != null)
            {
                GameTimerManager.Instance.StartTimer();
            }

            // WebGL 최적화 설정
            if (gameConfig != null)
            {
                Application.targetFrameRate = gameConfig.targetFrameRate;
                QualitySettings.shadows = gameConfig.enableShadows ? ShadowQuality.All : ShadowQuality.Disable;
            }
        }

        /// <summary>
        /// 플레이어를 시작 위치로 이동
        /// </summary>
        private void MovePlayerToStart()
        {
            if (player == null)
            {
                Debug.LogWarning("[GameStateManager] Player reference is not set!");
                return;
            }

            if (startTrackSegment != null)
            {
                // CharacterController가 있으면 비활성화 후 위치 변경
                CharacterController controller = player.GetComponent<CharacterController>();
                if (controller != null)
                {
                    controller.enabled = false;
                    player.position = startTrackSegment.StartPosition;
                    controller.enabled = true;
                    Debug.Log($"[GameStateManager] Player moved to StartPoint: {startTrackSegment.StartPosition}");
                }
                else
                {
                    player.position = startTrackSegment.StartPosition;
                    Debug.Log($"[GameStateManager] Player moved to StartPoint: {startTrackSegment.StartPosition}");
                }

                // 거리 계산 리셋 (RunnerController)
                RunnerController runnerController = player.GetComponent<RunnerController>();
                if (runnerController != null)
                {
                    runnerController.ResetDistance();
                }
            }
            else
            {
                Debug.LogWarning("[GameStateManager] StartTrackSegment is not set! Player will start at current position.");
            }
        }

        /// <summary>
        /// 상태 변경
        /// </summary>
        public void ChangeState(GameState newState)
        {
            if (currentState == newState) return;

            GameState previousState = currentState;
            currentState = newState;

            Debug.Log($"[GameState] {previousState} → {newState}");

            // 상태 변경 이벤트 발생
            OnStateChanged?.Invoke(previousState, newState);

            // 상태별 처리
            OnStateEnter(newState);
        }

        /// <summary>
        /// 상태 진입 시 처리
        /// </summary>
        private void OnStateEnter(GameState state)
        {
            switch (state)
            {
                case GameState.Running:
                    Time.timeScale = 1f;  // 게임 재개
                    if (GameTimerManager.Instance != null)
                    {
                        GameTimerManager.Instance.ResumeTimer();
                    }
                    break;

                case GameState.Quiz:
                    Time.timeScale = 1f;  // 게임 계속 진행 (일시정지 안함)
                    // 타이머도 계속 진행 (StopTimer 호출 안함)
                    break;

                case GameState.Result:
                    Time.timeScale = 0f;  // 게임 일시정지
                    if (GameTimerManager.Instance != null)
                    {
                        GameTimerManager.Instance.StopTimer();
                    }
                    break;

                case GameState.GameOver:
                    Time.timeScale = 0f;  // 게임 일시정지
                    if (GameTimerManager.Instance != null)
                    {
                        GameTimerManager.Instance.StopTimer();
                    }
                    break;

                case GameState.GameClear:
                    Time.timeScale = 0f;  // 게임 일시정지
                    if (GameTimerManager.Instance != null)
                    {
                        GameTimerManager.Instance.StopTimer();
                    }
                    Debug.Log("[GameStateManager] 🎉 GAME CLEAR! 🎉");
                    break;
            }
        }

        /// <summary>
        /// 퀴즈 시작
        /// </summary>
        public void StartQuiz()
        {
            ChangeState(GameState.Quiz);
        }

        /// <summary>
        /// 퀴즈 완료 (정답/오답 처리)
        /// </summary>
        public void CompleteQuiz(bool isCorrect, int scoreChange)
        {
            if (isCorrect)
            {
                gameStats.correctAnswers++;
            }
            else
            {
                gameStats.wrongAnswers++;
            }

            gameStats.totalScore += scoreChange;
            OnStatsUpdated?.Invoke(gameStats);

            // Running 상태로 복귀
            ChangeState(GameState.Running);
        }

        /// <summary>
        /// 결과 화면 표시
        /// </summary>
        public void ShowResult()
        {
            ChangeState(GameState.Result);
        }

        /// <summary>
        /// 게임 오버
        /// </summary>
        public void GameOver()
        {
            ChangeState(GameState.GameOver);
        }

        /// <summary>
        /// 게임 클리어 (골 도달)
        /// </summary>
        public void GameClear()
        {
            ChangeState(GameState.GameClear);
            Debug.Log($"[GameStateManager] 🎉 GAME CLEAR! Score: {gameStats.totalScore}, Distance: {gameStats.runDistance:F1}m, Time: {gameStats.playTime:F1}s");
        }

        /// <summary>
        /// 게임 재시작
        /// </summary>
        public void RestartGame()
        {
            // 퀴즈 진행 상황 리셋
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.ResetQuizProgress();
            }

            // 모든 QuizDoor 완전 리셋 (영구 플래그 포함)
            QuizDoor[] allDoors = FindObjectsOfType<QuizDoor>();
            foreach (QuizDoor door in allDoors)
            {
                door.FullReset();
            }
            Debug.Log($"[GameStateManager] {allDoors.Length}개의 QuizDoor 완전 리셋 완료!");

            // 모든 QuizDoorController 리셋
            QuizDoorController[] allControllers = FindObjectsOfType<QuizDoorController>();
            foreach (QuizDoorController controller in allControllers)
            {
                controller.Deactivate();
            }
            Debug.Log($"[GameStateManager] {allControllers.Length}개의 QuizDoorController 리셋 완료!");

            // 모든 QuizTrigger 리셋 (비활성화된 것도 포함)
            QuizTrigger[] allTriggers = FindObjectsOfType<QuizTrigger>(true);  // includeInactive = true
            foreach (QuizTrigger trigger in allTriggers)
            {
                trigger.ResetTrigger();
            }
            Debug.Log($"[GameStateManager] {allTriggers.Length}개의 QuizTrigger 리셋 완료!");

            // 모든 EndpointTrigger 리셋
            EndpointTrigger[] allEndpointTriggers = FindObjectsOfType<EndpointTrigger>(true);
            foreach (EndpointTrigger endpointTrigger in allEndpointTriggers)
            {
                endpointTrigger.ResetTrigger();
            }
            Debug.Log($"[GameStateManager] {allEndpointTriggers.Length}개의 EndpointTrigger 리셋 완료!");

            // 모든 GoalTrigger 리셋
            GoalTrigger[] allGoalTriggers = FindObjectsOfType<GoalTrigger>(true);
            foreach (GoalTrigger goalTrigger in allGoalTriggers)
            {
                goalTrigger.ResetTrigger();
            }
            Debug.Log($"[GameStateManager] {allGoalTriggers.Length}개의 GoalTrigger 리셋 완료!");

            // InitializeGame()이 플레이어 위치 초기화 포함
            InitializeGame();
        }

        /// <summary>
        /// 게임 종료
        /// </summary>
        public void QuitGame()
        {
            Debug.Log("[GameStateManager] Quitting game...");

            #if UNITY_EDITOR
                UnityEditor.EditorApplication.isPlaying = false;
            #else
                Application.Quit();
            #endif
        }

        /// <summary>
        /// 거리 추가
        /// </summary>
        public void AddDistance(float distance)
        {
            gameStats.runDistance += distance;
        }

        // 접근자
        public GameState CurrentState => currentState;
        public GameStats Stats => gameStats;
        public GameConfig Config => gameConfig;
    }
}
