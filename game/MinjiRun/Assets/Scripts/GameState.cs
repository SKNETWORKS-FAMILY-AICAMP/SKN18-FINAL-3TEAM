using System;

namespace minji_run
{
    /// <summary>
    /// 게임 상태 열거형
    /// </summary>
    public enum GameState
    {
        Running,    // 달리기 중
        Quiz,       // 퀴즈 풀이 중
        Result,     // 결과 화면
        GameOver,   // 게임 오버 (시간 초과)
        GameClear   // 게임 클리어 (골 도달)
    }

    /// <summary>
    /// 퀴즈 데이터 구조
    /// </summary>
    [Serializable]
    public class QuizData
    {
        public string question;          // 퀴즈 질문
        public string correctAnswer;     // 정답 1개
        public string[] wrongAnswers;    // 오답 2개
        public string explanation;       // 정답 설명
        public int rewardScore;          // 정답 시 점수
    }

    /// <summary>
    /// 퀴즈 목록 컨테이너
    /// </summary>
    [Serializable]
    public class QuizDataList
    {
        public QuizData[] quizzes;
    }

    /// <summary>
    /// 게임 통계
    /// </summary>
    [Serializable]
    public class GameStats
    {
        public int totalScore;          // 총 점수 (정답 개수)
        public int correctAnswers;      // 정답 개수
        public int wrongAnswers;        // 오답 개수
        public float runDistance;       // 달린 거리
        public float playTime;          // 플레이 시간

        public void Reset()
        {
            totalScore = 0;
            correctAnswers = 0;
            wrongAnswers = 0;
            runDistance = 0f;
            playTime = 0f;
        }
    }
}
