using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 퀴즈 문 관리 컨트롤러 (각 퀴즈 위치마다 배치)
    /// Unity에 배치된 3개의 문에 정답/오답을 랜덤으로 할당
    /// </summary>
    public class QuizDoorController : MonoBehaviour
    {
        [Header("Manual Door Placement")]
        [SerializeField] private QuizDoor[] quizDoors;  // Unity에서 직접 배치한 문들 (3개)
        [Tooltip("자식 오브젝트에서 QuizDoor를 자동으로 찾으려면 비워두세요")]

        [Header("Chain Settings")]
        [SerializeField] private QuizDoorController nextDoorController;  // 다음 퀴즈 문 컨트롤러
        [Tooltip("정답 시 자동으로 활성화할 다음 QuizDoorController (비워두면 체인 없음)")]
        [SerializeField] private float nextQuizDelay = 0f;  // 다음 퀴즈 생성 전 대기 시간 (즉시)

        [Header("Endpoint Settings")]
        [SerializeField] private bool isEndpoint = false;  // 마지막 문인지 여부
        [Tooltip("체크하면 이 문이 마지막 문이 됩니다. 통과 후 퀴즈가 나오지 않고 endpoint까지 달립니다.")]

        private bool isActivated = false;      // 이 컨트롤러가 현재 활성화되어 있는지
        private bool hasBeenActivated = false; // 한 번이라도 활성화된 적이 있는지 (중복 방지)

        private void Awake()
        {
            // QuizDoor가 할당되지 않았으면 자식 오브젝트에서 찾기
            if (quizDoors == null || quizDoors.Length == 0)
            {
                quizDoors = GetComponentsInChildren<QuizDoor>(true);
            }

            // 초기화 (게임 재시작 시에만 리셋 - Deactivate()에서 처리)
            // Awake()는 게임 중에도 호출될 수 있으므로 hasBeenActivated는 여기서 리셋하지 않음
            if (!hasBeenActivated)
            {
                isActivated = false;

                // 초기에는 모든 문 비활성화
                ResetAndHideDoors();
            }
        }

        /// <summary>
        /// 이 컨트롤러를 활성화하고 퀴즈 데이터 할당
        /// QuizTrigger 또는 이전 QuizDoorController에서 호출됨
        /// </summary>
        public void ActivateWithQuiz(QuizData quizData)
        {
            Debug.Log($"[QuizDoorController] ActivateWithQuiz 호출됨: {gameObject.name}, hasBeenActivated={hasBeenActivated}");

            // 이미 한 번 활성화되었으면 무시 (문당 한 번만 퀴즈)
            if (hasBeenActivated)
            {
                Debug.LogWarning($"[QuizDoorController] {gameObject.name} 이미 활성화되었습니다. 중복 퀴즈 방지!");
                return;
            }

            // QuizDoor 배열이 비어있으면 다시 찾기 (타이밍 이슈 방지)
            if (quizDoors == null || quizDoors.Length == 0)
            {
                quizDoors = GetComponentsInChildren<QuizDoor>(true);
            }

            // 먼저 기존 구독 제거 (안전장치)
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizAnswered -= OnQuizAnswered;
            }

            // 문에 새 퀴즈 데이터 할당 (한 번만)
            SpawnDoors(quizData);

            isActivated = true;
            hasBeenActivated = true;  // 활성화 기록

            // QuizManager 이벤트 즉시 구독 (플레이어가 빠르게 통과할 수 있으므로)
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizAnswered += OnQuizAnswered;
                Debug.Log($"[QuizDoorController] {gameObject.name} 이벤트 구독 완료");
            }

            Debug.Log($"[QuizDoorController] {gameObject.name} 퀴즈 활성화! Question: {quizData.question}");
        }

        /// <summary>
        /// 이 컨트롤러 비활성화 및 정리
        /// </summary>
        public void Deactivate()
        {
            isActivated = false;
            hasBeenActivated = false;  // 리셋 (재사용 가능하도록)

            // 모든 Invoke 취소
            CancelInvoke(nameof(ActivateNextController));

            // 이벤트 구독 해제
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizAnswered -= OnQuizAnswered;
            }

            ResetAndHideDoors();
        }

        /// <summary>
        /// Unity에 배치된 3개의 문에 퀴즈 데이터를 랜덤으로 할당
        /// </summary>
        public void SpawnDoors(QuizData quizData)
        {
            if (quizData == null || string.IsNullOrEmpty(quizData.correctAnswer) ||
                quizData.wrongAnswers == null || quizData.wrongAnswers.Length < 2)
            {
                Debug.LogError("[QuizDoorController] Invalid quiz data! Need 1 correct answer and 2 wrong answers.");
                return;
            }

            if (quizDoors == null || quizDoors.Length != 3)
            {
                Debug.LogError($"[QuizDoorController] Need exactly 3 quiz doors! Found: {quizDoors?.Length ?? 0}");
                return;
            }

            // 정답 1개 + 오답 2개를 하나의 배열로 합침
            List<string> allChoices = new List<string>
            {
                quizData.correctAnswer,
                quizData.wrongAnswers[0],
                quizData.wrongAnswers[1]
            };

            // 랜덤 셔플
            for (int i = 0; i < allChoices.Count; i++)
            {
                int randomIndex = Random.Range(i, allChoices.Count);
                string temp = allChoices[i];
                allChoices[i] = allChoices[randomIndex];
                allChoices[randomIndex] = temp;
            }

            // 각 문에 할당 (컨트롤러 참조도 함께 전달)
            for (int i = 0; i < 3; i++)
            {
                string choiceText = allChoices[i];
                bool isCorrect = (choiceText == quizData.correctAnswer);

                quizDoors[i].Initialize(i, choiceText, isCorrect, this);
            }
        }

        /// <summary>
        /// 모든 문 리셋 (파괴하지 않고 상태만 초기화)
        /// </summary>
        public void RemoveAllDoors()
        {
            // 문은 Unity에 배치되어 있으므로 파괴하지 않음
            // 대신 각 문의 상태를 리셋
            if (quizDoors != null)
            {
                foreach (QuizDoor door in quizDoors)
                {
                    if (door != null)
                    {
                        door.ResetDoor();
                    }
                }
            }
        }

        /// <summary>
        /// 모든 문 리셋하고 숨기기
        /// </summary>
        private void ResetAndHideDoors()
        {
            RemoveAllDoors();
        }

        /// <summary>
        /// 퀴즈 답변 후 처리
        /// </summary>
        private void OnQuizAnswered(bool isCorrect, int scoreChange, QuizDoor passedDoor, QuizDoorController sourceController)
        {
            // 이 컨트롤러가 활성화되어 있을 때만 처리
            if (!isActivated) return;

            // 다른 컨트롤러의 이벤트면 무시 (핵심 체크!)
            if (sourceController != this)
            {
                Debug.Log($"[QuizDoorController] {gameObject.name} 다른 컨트롤러({sourceController?.gameObject.name})의 이벤트 무시");
                return;
            }

            Debug.Log($"[QuizDoorController] {gameObject.name} 정답 처리 - isEndpoint: {isEndpoint}, nextDoorController: {(nextDoorController != null ? nextDoorController.name : "null")}");

            // 정답 문 강조 표시
            if (quizDoors != null)
            {
                foreach (QuizDoor door in quizDoors)
                {
                    if (door != null && door.IsCorrectAnswer)
                    {
                        door.ShowCorrectAnswer();
                    }
                }
            }

            // 정답이면 즉시 이벤트 구독 해제 후 다음 퀴즈 시작
            if (isCorrect)
            {
                // 이 컨트롤러가 관리하는 모든 문을 영구적으로 사용 불가로 만듦
                DisableAllDoorsInThisController();

                // 모든 Invoke 취소 (중복 호출 방지)
                CancelInvoke(nameof(ActivateNextController));

                // 즉시 이벤트 구독 해제 (중복 호출 방지)
                if (QuizManager.Instance != null)
                {
                    QuizManager.Instance.OnQuizAnswered -= OnQuizAnswered;
                }

                isActivated = false;

                // 마지막 문(endpoint)이면 다음 퀴즈를 활성화하지 않음
                // 플레이어는 endpoint까지 달려가서 게임 클리어
                if (isEndpoint)
                {
                    Debug.Log("[QuizDoorController] ✅ 마지막 문 통과! Endpoint까지 달리세요. 더 이상 퀴즈가 나오지 않습니다.");
                    // 퀴즈 UI 숨김
                    if (QuizManager.Instance != null)
                    {
                        QuizManager.Instance.HideQuizUI();
                    }
                }
                // 마지막 문이 아니면 다음 퀴즈 시작
                else if (nextDoorController != null)
                {
                    Debug.Log($"[QuizDoorController] ⏩ 다음 퀴즈 준비 중... ({nextQuizDelay}초 후 {nextDoorController.name} 활성화)");
                    // 중복 방지를 위해 먼저 CancelInvoke 후 Invoke
                    CancelInvoke(nameof(ActivateNextController));
                    Invoke(nameof(ActivateNextController), nextQuizDelay);
                }
                else
                {
                    Debug.Log("[QuizDoorController] ⚠️ isEndpoint=false이지만 nextDoorController가 null입니다. 퀴즈 체인이 여기서 끝납니다.");
                }
            }
            // 오답이면 문은 그대로 유지 (재도전 가능)
        }

        /// <summary>
        /// 이 컨트롤러가 관리하는 모든 문을 영구적으로 사용 불가로 만듦
        /// </summary>
        private void DisableAllDoorsInThisController()
        {
            if (quizDoors == null) return;

            foreach (QuizDoor door in quizDoors)
            {
                if (door != null)
                {
                    // 각 문을 영구적으로 사용 불가 상태로 만듦
                    door.MarkAsUsedPermanently();
                }
            }

            Debug.Log($"[QuizDoorController] {gameObject.name}의 모든 문({quizDoors.Length}개) 영구 사용 불가 처리!");
        }

        /// <summary>
        /// 다음 컨트롤러 활성화 (체인)
        /// </summary>
        private void ActivateNextController()
        {
            if (nextDoorController != null && QuizManager.Instance != null)
            {
                QuizManager.Instance.StartNewQuiz(nextDoorController);
            }
        }

        /// <summary>
        /// 오브젝트 파괴 시 이벤트 구독 해제
        /// </summary>
        private void OnDestroy()
        {
            // 모든 Invoke 취소
            CancelInvoke(nameof(ActivateNextController));

            // 이벤트 구독 해제
            if (QuizManager.Instance != null)
            {
                QuizManager.Instance.OnQuizAnswered -= OnQuizAnswered;
            }
        }

        // 접근자
        public int CurrentDoorCount => quizDoors?.Length ?? 0;
        public bool HasDoors => quizDoors != null && quizDoors.Length > 0;
    }
}
