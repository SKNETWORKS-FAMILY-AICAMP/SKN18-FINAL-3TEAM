import React, { useState, useEffect, useRef } from "react";

const IntroVideo = () => {
  const [videoSrc, setVideoSrc] = useState("");
  const videoRef = useRef(null);

  useEffect(() => {
    const videoList = [ //추후에 비디오 더 추가 가능
        "intro_greeting.webm",
        "intro_trouble.webm",
    ];

    const randomIndex = Math.floor(Math.random() * videoList.length);
    setVideoSrc(`/videos/${videoList[randomIndex]}`);;
  }, []);

  if (!videoSrc) return null;

  return (
    <div
      style={{
        width: "100%",
        height: "350px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        marginBottom: "20px",
        pointerEvents: "none",
      }}
    >
      <video
        ref={videoRef}
        src={videoSrc}
        autoPlay
        muted
        playsInline
        loop={false}
        
        // ▼ [최종 수정] 복잡한 로직 다 빼고 가장 심플하게 갑니다.
        onTimeUpdate={(e) => {
          const video = e.target;
          // 비디오 길이가 로드되지 않았으면 패스
          if (!video.duration) return;

          // "끝나기 0.5초 전"이면 무조건 멈춰라!
          // (0.5초는 사람 눈엔 똑같은 Idle 상태지만, 브라우저가 '끝'으로 인식하기엔 아주 먼 시간입니다.)
          // (따라서 절대 처음으로 되감기 되지 않습니다.)
          if (video.currentTime >= video.duration - 0.5) {
            video.pause();
          }
        }}
        
        style={{
          height: "100%",
          width: "auto",
          maxWidth: "100%",
          objectFit: "contain",
        }}
      />
    </div>
  );
};

export default IntroVideo;