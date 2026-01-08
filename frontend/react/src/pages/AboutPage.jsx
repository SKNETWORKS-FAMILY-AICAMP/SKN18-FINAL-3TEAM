const AboutPage = ({ onNavigate }) => {
  return (
    <div className="page active">
      <div className="about-page">
        <div className="about-bg"></div>
        <div className="about-webgl"></div>
        <div className="about-container">
          <div className="about-video">
            <video
              autoPlay
              loop
              muted
              playsInline
              style={{
                width: "100%",
                maxWidth: "400px",
                height: "auto",
                background: "transparent",
                backgroundColor: "transparent",
              }}
            >
              <source src="/videos/Minji_intro.webm" type="video/webm" />
            </video>
          </div>
          <div className="about-content">
            <div className="about-label">Meet the Storyteller</div>
            <h1 className="about-title">아가씨</h1>
            <p className="about-title-en">Agassi</p>
            <p className="about-desc">
              조선시대 양반가의 규수.
              <br />
              오백 년 역사의 기억을 품고
              <br />
              당신에게 조선의 이야기를 들려드립니다.
            </p>
            <div className="about-features">
              <div className="about-feature">
                <div className="about-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <div className="about-feature-text">역사 지식 기반</div>
              </div>
              <div className="about-feature">
                <div className="about-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div className="about-feature-text">자연스러운 대화</div>
              </div>
              <div className="about-feature">
                <div className="about-feature-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="about-feature-text">추론 과정 공개</div>
              </div>
            </div>
            <button
              className="about-cta"
              onClick={() => {
                if (onNavigate) {
                  onNavigate("question");
                } else {
                  window.location.hash = "question";
                }
              }}
            >
              아가씨에게 묻기
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutPage;
