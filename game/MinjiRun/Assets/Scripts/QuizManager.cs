using UnityEngine;
using System.Collections.Generic;
using System.Linq;
using System;

namespace minji_run
{
    /// <summary>
    /// 퀴즈 로드/채점/보상 관리자 (싱글톤)
    /// </summary>
    public class QuizManager : MonoBehaviour
    {
        public static QuizManager Instance { get; private set; }

        [Header("Quiz Settings")]
        [SerializeField] private TextAsset quizJsonFile;  // Resources에서 로드할 JSON 파일
        [SerializeField] private bool shuffleQuizzes = true;  // 퀴즈 순서 섞기

        [Header("Current Quiz")]
        [SerializeField] private int currentQuizIndex = -1;
        private QuizData currentQuiz;
        private List<QuizData> quizList = new List<QuizData>();
        private List<int> usedQuizIndices = new List<int>();  // 이미 출제된 퀴즈

        // 이벤트
        public event Action<QuizData> OnQuizLoaded;        // 퀴즈 로드됨
        public event Action<bool, int, QuizDoor, QuizDoorController> OnQuizAnswered;     // 퀴즈 응답 (정답 여부, 점수 변화, 통과한 문, 어느 컨트롤러)
        public event Action<float> OnQuizTimeUpdated;      // 남은 시간 업데이트

        private float quizTimeRemaining;
        private bool isQuizActive = false;

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

        private void Start()
        {
            LoadQuizzes();
        }

        private void Update()
        {
            // 퀴즈 활성화 중일 때 타이머 업데이트
            if (isQuizActive)
            {
                quizTimeRemaining -= Time.unscaledDeltaTime;  // Time.timeScale 영향 안받음
                OnQuizTimeUpdated?.Invoke(Mathf.Max(0, quizTimeRemaining));

                // 시간 초과 (하지만 퀴즈는 계속 활성화 - 문 통과 가능, 페널티 없음)
                if (quizTimeRemaining <= 0f)
                {
                    quizTimeRemaining = 0f;  // 0으로 고정
                    // isQuizActive는 그대로 true 유지 - 문 통과 시 다음 퀴즈로 진행
                    // 페널티 없음 - 문만 통과하면 됨!
                }
            }
        }

        /// <summary>
        /// JSON에서 퀴즈 데이터 로드
        /// </summary>
        private void LoadQuizzes()
        {
            try
            {
                if (quizJsonFile == null)
                {
                    // JSON 파일이 없으면 Resources에서 로드 시도
                    quizJsonFile = Resources.Load<TextAsset>("Quizzes/quiz_data");
                }

                if (quizJsonFile != null)
                {
                    QuizDataList dataList = JsonUtility.FromJson<QuizDataList>(quizJsonFile.text);
                    quizList = dataList.quizzes.ToList();

                    if (shuffleQuizzes)
                    {
                        ShuffleList(quizList);
                    }

                    Debug.Log($"[QuizManager] Loaded {quizList.Count} quizzes");
                }
                else
                {
                    Debug.LogWarning("[QuizManager] Quiz JSON file not found! Creating sample quiz.");
                    CreateSampleQuiz();
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[QuizManager] Failed to load quizzes: {e.Message}");
                CreateSampleQuiz();
            }
        }

        /// <summary>
        /// 샘플 퀴즈 생성 (JSON 파일이 없을 때)
        /// </summary>
        private void CreateSampleQuiz()
        {
            quizList = new List<QuizData>
            {
                new QuizData
                {
                    question = "대한민국의 수도는?",
                    correctAnswer = "서울",
                    wrongAnswers = new string[] { "부산", "인천" },
                    explanation = "대한민국의 수도는 서울입니다.",
                    rewardScore = 100
                },
                new QuizData
                {
                    question = "조선을 건국한 사람은?",
                    correctAnswer = "이성계",
                    wrongAnswers = new string[] { "왕건", "박혁거세" },
                    explanation = "이성계가 1392년 조선을 건국했습니다.",
                    rewardScore = 100
                }
            };
        }

        /// <summary>
        /// 새로운 퀴즈 시작 (특정 QuizDoorController에 할당)
        /// </summary>
        public void StartNewQuiz(QuizDoorController doorController)
        {
            if (doorController == null)
            {
                Debug.LogError("[QuizManager] doorController is null!");
                return;
            }

            if (quizList.Count == 0)
            {
                Debug.LogError("[QuizManager] No quizzes available!");
                return;
            }

            // 아직 안 푼 퀴즈 중에서 랜덤 선택
            List<int> availableIndices = new List<int>();
            for (int i = 0; i < quizList.Count; i++)
            {
                if (!usedQuizIndices.Contains(i))
                {
                    availableIndices.Add(i);
                }
            }

            // 모든 퀴즈를 다 풀었으면 더 이상 퀴즈가 나오지 않음
            if (availableIndices.Count == 0)
            {
                Debug.Log("[QuizManager] All quizzes completed! No more quizzes available.");
                return;
            }

            currentQuizIndex = availableIndices[UnityEngine.Random.Range(0, availableIndices.Count)];
            usedQuizIndices.Add(currentQuizIndex);

            currentQuiz = quizList[currentQuizIndex];

            // 퀴즈 시작
            isQuizActive = true;
            quizTimeRemaining = GameStateManager.Instance.Config.quizTimeLimit;

            // 특정 QuizDoorController에 퀴즈 할당
            doorController.ActivateWithQuiz(currentQuiz);

            // 이벤트 발생 (UI 업데이트 등을 위해 유지)
            OnQuizLoaded?.Invoke(currentQuiz);
            Debug.Log($"[QuizManager] Quiz started: {currentQuiz.question}");
        }

        /// <summary>
        /// 답안 제출 (정답 문을 통과했을 때만 호출됨)
        /// </summary>
        public void SubmitAnswer(int selectedIndex, QuizDoor passedDoor, QuizDoorController controller)
        {
            Debug.Log($"[QuizManager] SubmitAnswer 호출됨! isQuizActive={isQuizActive}, Door: {passedDoor?.gameObject.name}");

            if (!isQuizActive)
            {
                Debug.LogWarning("[QuizManager] ⚠️ isQuizActive=false! 퀴즈가 아직 활성화되지 않았거나 이미 종료되었습니다.");
                return;
            }

            // QuizDoor에서 이미 정답 검증을 했으므로 여기서는 정답만 처리
            Debug.Log($"[QuizManager] ✅ 정답! Door: {passedDoor?.gameObject.name}, Controller: {controller?.gameObject.name}");
            isQuizActive = false;

            // 정답: 보너스 시간 추가
            if (GameTimerManager.Instance != null)
            {
                GameTimerManager.Instance.AddBonusTime();
            }

            // 이벤트 발생 (어떤 문이 통과되었는지 + 어느 컨트롤러인지 전달)
            OnQuizAnswered?.Invoke(true, 1, passedDoor, controller);

            // GameStateManager에 결과 전달
            GameStateManager.Instance.CompleteQuiz(true, 1);
        }

        /// <summary>
        /// 리스트 셔플 (Fisher-Yates)
        /// </summary>
        private void ShuffleList<T>(List<T> list)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = UnityEngine.Random.Range(0, i + 1);
                T temp = list[i];
                list[i] = list[j];
                list[j] = temp;
            }
        }

        /// <summary>
        /// 퀴즈 진행 상황 리셋 (게임 재시작 시 호출)
        /// </summary>
        public void ResetQuizProgress()
        {
            usedQuizIndices.Clear();
            currentQuizIndex = -1;
            currentQuiz = null;
            isQuizActive = false;
            Debug.Log("[QuizManager] Quiz progress reset");
        }

        /// <summary>
        /// 퀴즈 UI 숨기기 (마지막 문 통과 후)
        /// </summary>
        public void HideQuizUI()
        {
            isQuizActive = false;
            Debug.Log("[QuizManager] Quiz UI hidden - final door passed");
        }

        // 접근자
        public QuizData CurrentQuiz => currentQuiz;
        public float TimeRemaining => quizTimeRemaining;
        public bool IsQuizActive => isQuizActive;
    }
}
