using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace minji_run
{
    /// <summary>
    /// UI 패널 및 HUD 관리자 (싱글톤)
    /// HUD, Quiz Panel, Result Panel 스위치
    /// </summary>
    public class UIManager : MonoBehaviour
    {
        public static UIManager Instance { get; private set; }

        [Header("Panels")]
        [SerializeField] private GameObject hudPanel;
        [SerializeField] private GameObject quizPanel;
        [SerializeField] private GameObject resultPanel;
        [SerializeField] private GameObject gameOverPanel;

        [Header("HUD Elements")]
        [SerializeField] private TextMeshProUGUI scoreText;
        [SerializeField] private TextMeshProUGUI distanceText;
        [SerializeField] private TextMeshProUGUI gameTimerText;  // 게임 타이머 (100초)
        [SerializeField] private Image dashGaugeFillImage;       // 대쉬 게이지 (Fill Image)

        [Header("Quiz Panel Elements")]
        [SerializeField] private TextMeshProUGUI questionText;

        [Header("Result Panel Elements")]
        [SerializeField] private TextMeshProUGUI resultScoreText;
        [SerializeField] private TextMeshProUGUI resultDistanceText;
        [SerializeField] private TextMeshProUGUI resultTimeText;
        [SerializeField] private TextMeshProUGUI resultCorrectText;
        [SerializeField] private TextMeshProUGUI resultWrongText;
        [SerializeField] private Button restartButton;
        [SerializeField] private Button quitButton;

        [Header("Colors")]
        [SerializeField] private Color correctColor = Color.green;
        [SerializeField] private Color wrongColor = Color.red;
        [SerializeField] private Color normalColor = Color.white;

        private QuizData currentQuiz;
        private RunnerController playerController;

        private void Awake()
        {
            // 싱글톤 설정
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;

            // ⭐ 이벤트 구독을 Awake에서 먼저 해야 QuizManager.Start()에서 발생하는 이벤트를 받을 수 있음

            // GameStateManager 이벤트 구독 (지연 구독 방식)
            StartCoroutine(SubscribeToManagersWhenReady());
        }

        private System.Collections.IEnumerator SubscribeToManagersWhenReady()
        {
            // 모든 Manager의 Awake()가 완료될 때까지 대기
            yield return null;

            // 이벤트 구독
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.OnStateChanged += OnGameStateChanged;
                GameStateManager.Instance.OnStatsUpdated += UpdateHUD;
            }
            else
            {
                Debug.LogError("[UIManager] GameStateManager.Instance is NULL!");
            }

            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizLoaded += OnQuizLoaded;
                QuizManager.Instance.OnQuizAnswered += OnQuizAnswered;
            }
            else
            {
                Debug.LogWarning("[UIManager] QuizManager.Instance is NULL in Awake!");
            }

            if (GameTimerManager.Instance != null)
            {
                GameTimerManager.Instance.OnTimerUpdated += UpdateGameTimer;
                GameTimerManager.Instance.OnTimerExpired += OnGameTimerExpired;
            }
        }

        private void Start()
        {
            // 플레이어 컨트롤러 찾기
            GameObject player = GameObject.FindGameObjectWithTag("Player");
            if (player != null)
            {
                playerController = player.GetComponent<RunnerController>();
            }
            else
            {
                Debug.LogError("[UIManager] Player object not found! Make sure Player has 'Player' tag.");
            }

            // 대시 게이지 UI 확인
            if (dashGaugeFillImage == null)
            {
                Debug.LogWarning("[UIManager] Dash Gauge Fill Image not assigned in Inspector!");
            }

            // 버튼 리스너 등록
            if (restartButton != null)
                restartButton.onClick.AddListener(OnRestartButtonClicked);

            if (quitButton != null)
                quitButton.onClick.AddListener(OnQuitButtonClicked);

            // 초기 UI 설정
            ShowPanel(hudPanel);
        }

        private void Update()
        {
            // 대쉬 게이지 업데이트
            UpdateDashGauge();

            // HUD 업데이트 (매 프레임)
            if (GameStateManager.Instance != null)
            {
                UpdateHUD(GameStateManager.Instance.Stats);
            }
        }

        private void OnDestroy()
        {
            // 이벤트 구독 해제
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.OnStateChanged -= OnGameStateChanged;
                GameStateManager.Instance.OnStatsUpdated -= UpdateHUD;
            }

            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizLoaded -= OnQuizLoaded;
                QuizManager.Instance.OnQuizAnswered -= OnQuizAnswered;
            }

            if (GameTimerManager.Instance != null)
            {
                GameTimerManager.Instance.OnTimerUpdated -= UpdateGameTimer;
                GameTimerManager.Instance.OnTimerExpired -= OnGameTimerExpired;
            }
        }

        /// <summary>
        /// 게임 상태 변경 시 호출
        /// </summary>
        private void OnGameStateChanged(GameState previousState, GameState newState)
        {
            switch (newState)
            {
                case GameState.Running:
                    ShowPanel(hudPanel);
                    break;

                case GameState.Quiz:
                    ShowPanel(quizPanel);
                    break;

                case GameState.Result:
                    ShowPanel(resultPanel);
                    UpdateResultPanel();
                    break;

                case GameState.GameOver:
                    ShowPanel(gameOverPanel);
                    break;

                case GameState.GameClear:
                    ShowPanel(resultPanel);
                    UpdateResultPanel();
                    break;
            }
        }

        /// <summary>
        /// 특정 패널만 표시
        /// </summary>
        private void ShowPanel(GameObject panel)
        {
            hudPanel?.SetActive(panel == hudPanel);
            quizPanel?.SetActive(panel == quizPanel);
            resultPanel?.SetActive(panel == resultPanel);
            gameOverPanel?.SetActive(panel == gameOverPanel);
        }

        /// <summary>
        /// HUD 업데이트
        /// </summary>
        private void UpdateHUD(GameStats stats)
        {
            if (scoreText != null)
                scoreText.text = $"점수: {stats.totalScore}";

            if (distanceText != null)
                distanceText.text = $"거리: {stats.runDistance:F1}m";
        }

        /// <summary>
        /// 퀴즈 로드됨
        /// </summary>
        private void OnQuizLoaded(QuizData quiz)
        {
            currentQuiz = quiz;

            // 퀴즈 패널 활성화
            if (quizPanel != null)
            {
                quizPanel.SetActive(true);

                // Quiz Panel의 Image 컴포넌트 Alpha 설정
                Image panelImage = quizPanel.GetComponent<Image>();
                if (panelImage != null)
                {
                    Color panelColor = panelImage.color;
                    panelColor.a = 0.8f;  // 반투명 검정
                    panelImage.color = panelColor;
                    panelImage.enabled = true;
                }
            }

            // 질문 표시
            if (questionText != null)
            {
                questionText.text = quiz.question;
                questionText.gameObject.SetActive(true);
                questionText.color = Color.white;
                // Font Size는 Inspector 설정 사용 (코드에서 설정하지 않음)
                questionText.enabled = true;
            }

            // 3초 후 질문 숨기고 문 생성
            Invoke(nameof(HideQuestionAndSpawnDoors), 3f);
        }

        /// <summary>
        /// 질문 숨기고 문 생성
        /// </summary>
        private void HideQuestionAndSpawnDoors()
        {
            // 질문 숨김
            if (questionText != null)
            {
                questionText.gameObject.SetActive(false);
            }

            // 퀴즈 패널 숨김
            if (quizPanel != null)
            {
                quizPanel.SetActive(false);
            }

            // HUD 다시 표시
            if (hudPanel != null)
            {
                hudPanel.SetActive(true);
            }

            // 게임 재개
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.ChangeState(GameState.Running);
            }
        }

        /// <summary>
        /// 퀴즈 답변 제출됨
        /// </summary>
        private void OnQuizAnswered(bool isCorrect, int scoreChange, QuizDoor passedDoor, QuizDoorController controller)
        {
            if (isCorrect)
            {
                // 정답: 문 제거는 QuizDoorController에서 처리
                // 게임 계속 진행
            }
            else
            {
                // 오답: 체크포인트로 복귀는 QuizManager에서 처리
                // 문은 그대로 유지하고 다시 도전
            }
        }

        /// <summary>
        /// 퀴즈 패널 닫기
        /// </summary>
        private void CloseQuizPanel()
        {
            // GameStateManager가 이미 Running으로 변경했으므로 패널만 닫으면 됨
        }

        /// <summary>
        /// 결과 패널 업데이트
        /// </summary>
        private void UpdateResultPanel()
        {
            if (GameStateManager.Instance == null) return;

            GameStats stats = GameStateManager.Instance.Stats;

            if (resultScoreText != null)
                resultScoreText.text = $"점수: {stats.totalScore}";

            if (resultDistanceText != null)
                resultDistanceText.text = $"거리: {stats.runDistance:F1}m";

            if (resultTimeText != null)
            {
                int minutes = Mathf.FloorToInt(stats.playTime / 60f);
                int seconds = Mathf.FloorToInt(stats.playTime % 60f);
                resultTimeText.text = $"시간: {minutes:00}:{seconds:00}";
            }

            if (resultCorrectText != null)
                resultCorrectText.text = $"정답: {stats.correctAnswers}";

            if (resultWrongText != null)
                resultWrongText.text = $"오답: {stats.wrongAnswers}";
        }

        /// <summary>
        /// 재시작 버튼 클릭
        /// </summary>
        private void OnRestartButtonClicked()
        {
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.RestartGame();
            }
        }

        /// <summary>
        /// 종료 버튼 클릭
        /// </summary>
        private void OnQuitButtonClicked()
        {
            #if UNITY_EDITOR
                UnityEditor.EditorApplication.isPlaying = false;
            #else
                Application.Quit();
            #endif
        }

        /// <summary>
        /// 게임 타이머 업데이트
        /// </summary>
        private void UpdateGameTimer(float timeRemaining)
        {
            if (gameTimerText != null)
            {
                int minutes = Mathf.FloorToInt(timeRemaining / 60f);
                int seconds = Mathf.FloorToInt(timeRemaining % 60f);
                gameTimerText.text = $"제한시간: {minutes:00}:{seconds:00}";

                // 시간이 얼마 남지 않으면 빨간색으로 표시
                if (timeRemaining <= 10f)
                {
                    gameTimerText.color = Color.red;
                }
                else if (timeRemaining <= 30f)
                {
                    gameTimerText.color = Color.yellow;
                }
                else
                {
                    gameTimerText.color = Color.white;
                }
            }
        }

        /// <summary>
        /// 게임 타이머 종료
        /// </summary>
        private void OnGameTimerExpired()
        {
            if (GameStateManager.Instance != null)
            {
                GameStateManager.Instance.GameOver();
            }
        }

        /// <summary>
        /// 대쉬 게이지 업데이트
        /// </summary>
        private void UpdateDashGauge()
        {
            if (dashGaugeFillImage == null)
            {
                return;  // UI가 없으면 업데이트 안함
            }

            if (playerController == null)
            {
                return;  // 플레이어가 없으면 업데이트 안함
            }

            // 대쉬 게이지: 0~100 → 0~1
            float gaugePercent = playerController.DashGaugePercent;
            dashGaugeFillImage.fillAmount = gaugePercent;

            // 색상 변경 (게이지 없음: 회색, 게이지 있음: 흰색)
            if (playerController.DashGauge <= 0f)
            {
                dashGaugeFillImage.color = new Color(0.5f, 0.5f, 0.5f);  // 게이지 없음
            }
            else
            {
                dashGaugeFillImage.color = Color.white;  // 게이지 있음
            }
        }
    }
}
