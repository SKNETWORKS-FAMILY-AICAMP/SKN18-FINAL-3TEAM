import { useState, useRef, useEffect } from "react";
import ReactPlayer from "react-player";

// 5초 뒤로 가기 아이콘 (이중 왼쪽 화살표)
const SkipBackwardIcon = ({ size = 48, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M11 18L5 12L11 6M19 18L13 12L19 6"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// 5초 앞으로 가기 아이콘 (이중 오른쪽 화살표)
const SkipForwardIcon = ({ size = 48, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M13 6L19 12L13 18M5 6L11 12L5 18"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// 재생 아이콘
const PlayCenterIcon = ({ size = 48, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M8 5v14l11-7z" />
  </svg>
);

// 일시정지 아이콘
const PauseCenterIcon = ({ size = 48, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <rect x="6" y="4" width="4" height="16" />
    <rect x="14" y="4" width="4" height="16" />
  </svg>
);

const VideoPlayer = ({ videoUrl = "/videos/test-video.mp4" }) => {
  const [playing, setPlaying] = useState(false);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [error, setError] = useState(null);
  const playerRef = useRef(null);
  const controlsTimeoutRef = useRef(null);

  // videoUrl이 변경되면 에러 상태 초기화
  useEffect(() => {
    console.log("VideoPlayer - videoUrl 변경:", videoUrl);
    setError(null);
    setPlaying(false);
    setPlayed(0);
    setDuration(0);
  }, [videoUrl]);

  const handlePlayPause = () => {
    setPlaying(!playing);
  };

  const handleProgress = (state) => {
    if (!seeking) {
      setPlayed(state.played);
    }
  };

  const handleDuration = (dur) => {
    setDuration(dur);
  };

  const handleSkipBackward = () => {
    if (!playerRef.current || typeof playerRef.current.seekTo !== "function")
      return;
    const currentTime = playerRef.current.getCurrentTime() || 0;
    const newTime = Math.max(0, currentTime - 5);
    playerRef.current.seekTo(newTime);
  };

  const handleSkipForward = () => {
    if (!playerRef.current || typeof playerRef.current.seekTo !== "function")
      return;
    const currentTime = playerRef.current.getCurrentTime() || 0;
    const newTime = Math.min(duration, currentTime + 5);
    playerRef.current.seekTo(newTime);
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    if (playing) {
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
  };

  const handleMouseLeave = () => {
    if (playing) {
      setShowControls(false);
    }
  };

  return (
    <div
      style={{
        width: "100%",
        aspectRatio: "16/9",
        backgroundColor: "#000",
        borderRadius: "16px",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={handlePlayPause}
    >
      <ReactPlayer
        ref={playerRef}
        url={videoUrl}
        playing={playing}
        width="100%"
        height="100%"
        onProgress={handleProgress}
        onDuration={handleDuration}
        onError={(err) => {
          console.error("영상 로드 오류:", err, "URL:", videoUrl);
          console.error("에러 타입:", err?.type, "에러 메시지:", err?.message);
          setError(`영상을 로드할 수 없습니다: ${videoUrl}`);
        }}
        onReady={() => {
          setError(null);
          console.log("영상 준비 완료:", videoUrl);
          if (playerRef.current) {
            try {
              const dur = playerRef.current.getDuration();
              if (dur && dur > 0) {
                console.log("영상 길이 (getDuration):", dur);
                setDuration(dur);
              }
            } catch (e) {
              console.warn("영상 길이 가져오기 실패:", e);
            }
          }
        }}
        onStart={() => {
          console.log("영상 시작:", videoUrl);
          setError(null);
        }}
        controls={false}
        config={{
          file: {
            attributes: {
              controlsList: "nodownload",
              preload: "metadata",
              crossOrigin: "anonymous",
            },
            forceVideo: true,
            forceHLS: false,
            forceDASH: false,
          },
        }}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
        }}
      />

      {/* 에러 메시지 */}
      {error && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "#fff",
            fontSize: "14px",
            textAlign: "center",
            zIndex: 20,
          }}
        >
          {error}
        </div>
      )}

      {/* 중앙 컨트롤 (5초 뒤로, 재생/일시정지, 5초 앞으로) */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex",
          alignItems: "center",
          gap: "40px",
          opacity: showControls ? 1 : 0,
          transition: "opacity 0.3s ease",
          zIndex: 10,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 5초 뒤로 */}
        <button
          onClick={handleSkipBackward}
          style={{
            width: "60px",
            height: "60px",
            borderRadius: "50%",
            backgroundColor: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "transform 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
          }}
        >
          <SkipBackwardIcon size={50} color="#fff" />
        </button>

        {/* 재생/일시정지 */}
        <button
          onClick={handlePlayPause}
          style={{
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            backgroundColor: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "transform 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
          }}
        >
          {playing ? (
            <PauseCenterIcon size={60} color="#fff" />
          ) : (
            <PlayCenterIcon size={60} color="#fff" />
          )}
        </button>

        {/* 5초 앞으로 */}
        <button
          onClick={handleSkipForward}
          style={{
            width: "60px",
            height: "60px",
            borderRadius: "50%",
            backgroundColor: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "transform 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
          }}
        >
          <SkipForwardIcon size={50} color="#fff" />
        </button>
      </div>

      {/* 하단 플레이바 */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "20px",
          background: "linear-gradient(to top, rgba(0,0,0,0.8), transparent)",
          opacity: showControls ? 1 : 0,
          transition: "opacity 0.3s ease",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 시간 표시 */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "8px",
            color: "#fff",
            fontSize: "14px",
          }}
        >
          <span>{formatTime(played * duration)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        {/* 플레이바 */}
        <div
          style={{
            width: "100%",
            height: "6px",
            backgroundColor: "rgba(255, 255, 255, 0.3)",
            borderRadius: "3px",
            position: "relative",
            cursor: "pointer",
          }}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const percent = (e.clientX - rect.left) / rect.width;
            if (
              playerRef.current &&
              typeof playerRef.current.seekTo === "function"
            ) {
              playerRef.current.seekTo(percent);
            }
            setPlayed(percent);
          }}
        >
          {/* 재생된 부분 (빨간색) */}
          <div
            style={{
              width: `${played * 100}%`,
              height: "100%",
              backgroundColor: "#e63946",
              borderRadius: "3px",
              position: "relative",
            }}
          >
            {/* 플레이바 핸들 */}
            <div
              style={{
                position: "absolute",
                right: "-8px",
                top: "50%",
                transform: "translateY(-50%)",
                width: "16px",
                height: "16px",
                backgroundColor: "#e63946",
                borderRadius: "50%",
                cursor: "grab",
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setSeeking(true);
                const handleMouseMove = (moveEvent) => {
                  const rect =
                    e.currentTarget.parentElement.parentElement.getBoundingClientRect();
                  const percent = Math.max(
                    0,
                    Math.min(1, (moveEvent.clientX - rect.left) / rect.width)
                  );
                  setPlayed(percent);
                };
                const handleMouseUp = () => {
                  if (
                    playerRef.current &&
                    typeof playerRef.current.seekTo === "function"
                  ) {
                    playerRef.current.seekTo(played);
                  }
                  setSeeking(false);
                  document.removeEventListener("mousemove", handleMouseMove);
                  document.removeEventListener("mouseup", handleMouseUp);
                };
                document.addEventListener("mousemove", handleMouseMove);
                document.addEventListener("mouseup", handleMouseUp);
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
