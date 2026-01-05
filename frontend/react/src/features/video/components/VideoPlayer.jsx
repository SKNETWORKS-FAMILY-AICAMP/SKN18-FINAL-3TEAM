import { useState, useRef, useEffect } from "react";

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

// 전체화면 아이콘
const FullscreenIcon = ({ size = 24, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M8 3H5C3.89543 3 3 3.89543 3 5V8M21 8V5C21 3.89543 20.1046 3 19 3H16M16 21H19C20.1046 21 21 20.1046 21 19V16M3 16V19C3 20.1046 3.89543 21 5 21H8"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// 전체화면 나가기 아이콘
const FullscreenExitIcon = ({ size = 24, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M8 3V8H3M16 3V8H21M16 21V16H21M8 21V16H3"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const VideoPlayer = ({
  videoUrl = "/videos/test-video.mp4",
  initialTime = 0,
  onPlayStart,
  onTimeUpdate,
  onPause,
  onEnded,
}) => {
  const [playing, setPlaying] = useState(false);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const playerRef = useRef(null);
  const containerRef = useRef(null);
  const controlsTimeoutRef = useRef(null);
  const hasPlayedRef = useRef(false); // 재생 이벤트 중복 방지
  const hasAppliedInitialTimeRef = useRef(false);

  // videoUrl이 변경되면 에러 상태 초기화
  useEffect(() => {
    setError(null);
    setPlaying(false); // 재생 중단
    setPlayed(0);
    setDuration(0);
    hasPlayedRef.current = false; // 재생 플래그 초기화
    hasAppliedInitialTimeRef.current = false;
  }, [videoUrl]);

  // playing 상태에 따라 video 재생/일시정지
  useEffect(() => {
    const video = playerRef.current;
    if (!video) return;

    if (playing) {
      video.play().catch((err) => {
        console.error("재생 실패:", err);
        setPlaying(false);
      });

      // 최초 재생 시 onPlayStart 콜백 호출 (한 번만)
      if (!hasPlayedRef.current && onPlayStart) {
        hasPlayedRef.current = true;
        onPlayStart();
      }
    } else {
      video.pause();
    }
  }, [playing, onPlayStart]);

  const handlePlayPause = () => {
    // 에러가 있으면 재생하지 않음
    if (error) return;
    setPlaying(!playing);
  };

  const handlePlayStart = () => {
    if (typeof onPlayStart === "function") {
      onPlayStart();
    }
  };

  const handleSkipBackward = () => {
    const video = playerRef.current;
    if (!video) return;
    video.currentTime = Math.max(0, video.currentTime - 5);
  };

  const handleSkipForward = () => {
    const video = playerRef.current;
    if (!video) return;
    video.currentTime = Math.min(duration, video.currentTime + 5);
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

  const handleFullscreen = () => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      // 전체화면 진입
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      } else if (containerRef.current.webkitRequestFullscreen) {
        // Safari
        containerRef.current.webkitRequestFullscreen();
      } else if (containerRef.current.mozRequestFullScreen) {
        // Firefox
        containerRef.current.mozRequestFullScreen();
      } else if (containerRef.current.msRequestFullscreen) {
        // IE/Edge
        containerRef.current.msRequestFullscreen();
      }
    } else {
      // 전체화면 나가기
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        // Safari
        document.webkitExitFullscreen();
      } else if (document.mozCancelFullScreen) {
        // Firefox
        document.mozCancelFullScreen();
      } else if (document.msExitFullscreen) {
        // IE/Edge
        document.msExitFullscreen();
      }
    }
  };

  // 전체화면 상태 변경 감지
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(
        !!(
          document.fullscreenElement ||
          document.webkitFullscreenElement ||
          document.mozFullScreenElement ||
          document.msFullscreenElement
        )
      );
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    document.addEventListener("mozfullscreenchange", handleFullscreenChange);
    document.addEventListener("MSFullscreenChange", handleFullscreenChange);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener(
        "webkitfullscreenchange",
        handleFullscreenChange
      );
      document.removeEventListener(
        "mozfullscreenchange",
        handleFullscreenChange
      );
      document.removeEventListener(
        "MSFullscreenChange",
        handleFullscreenChange
      );
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        aspectRatio: "16/9",
        backgroundColor: "#000",
        borderRadius: isFullscreen ? "0" : "16px",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={handlePlayPause}
    >
      <video
        ref={playerRef}
        src={videoUrl}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "contain",
        }}
        playsInline
        preload="metadata"
        onPlay={handlePlayStart}
        onPause={() => {
          if (typeof onPause === "function") {
            onPause();
          }
        }}
        onEnded={() => {
          if (typeof onEnded === "function") {
            onEnded();
          }
        }}
        onLoadedMetadata={(e) => {
          setError(null);
          const dur = e.target.duration;
          setDuration(dur);
          if (!hasAppliedInitialTimeRef.current && initialTime > 0) {
            const safeTime = Math.min(initialTime, dur || initialTime);
            e.target.currentTime = safeTime;
            if (dur > 0) {
              setPlayed(safeTime / dur);
            }
            hasAppliedInitialTimeRef.current = true;
          }
        }}
        onTimeUpdate={(e) => {
          if (typeof onTimeUpdate === "function") {
            onTimeUpdate(e.target.currentTime);
          }
          if (!seeking && duration > 0) {
            setPlayed(e.target.currentTime / duration);
          }
        }}
        onError={(e) => {
          console.error("영상 로드 오류:", e.target.error, "URL:", videoUrl);
          setError(`영상을 로드할 수 없습니다: ${videoUrl}`);
          setPlaying(false);
        }}
        onCanPlay={() => {
          // 영상 재생 가능 상태
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
        {/* 시간 표시 및 전체화면 버튼 */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "8px",
            color: "#fff",
            fontSize: "14px",
          }}
        >
          <span>{formatTime(played * duration)}</span>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span>{formatTime(duration)}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleFullscreen();
              }}
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "4px",
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
              {isFullscreen ? (
                <FullscreenExitIcon size={20} color="#fff" />
              ) : (
                <FullscreenIcon size={20} color="#fff" />
              )}
            </button>
          </div>
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
            const video = playerRef.current;
            if (video && duration > 0) {
              video.currentTime = percent * duration;
              setPlayed(percent);
            }
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
                  const video = playerRef.current;
                  if (video && duration > 0) {
                    video.currentTime = played * duration;
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
