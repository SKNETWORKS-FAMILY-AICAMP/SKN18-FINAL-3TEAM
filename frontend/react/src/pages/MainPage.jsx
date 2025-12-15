import { COLORS } from "../constants/theme";
import VideoGrid from "../features/video/components/VideoGrid";

const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const videos = [
    { id: 1, tags: "#전쟁사 #정조", title: "제목" },
    { id: 2, tags: "#발명품 #세종", title: "제목" },
    { id: 3, tags: "#전쟁사 #정조", title: "제목" },
    { id: 4, tags: "#전쟁사 #정조", title: "제목" },
    { id: 5, tags: "#전쟁사 #정조", title: "제목" },
    { id: 6, tags: "#전쟁사 #정조", title: "제목" },
  ];

  return (
    <main
      style={{
        padding: "80px 60px 40px 60px",
        backgroundColor: COLORS.background,
        minHeight: "100vh",
      }}
    >
      <div
        style={{
          marginBottom: "40px",
        }}
      >
        <h1
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: "clamp(48px, 8vw, 120px)",
            fontWeight: "700",
            color: "#effd9a",
            margin: 0,
            lineHeight: "1.1",
            letterSpacing: "-0.01em",
            transform: "scaleX(1.03)",
            transformOrigin: "left",
          }}
        >
          {isLoggedIn ? "RECOMMEND" : "POPULAR"}
        </h1>
      </div>

      <VideoGrid videos={videos} onVideoClick={onVideoClick} />
    </main>
  );
};

export default MainPage;
