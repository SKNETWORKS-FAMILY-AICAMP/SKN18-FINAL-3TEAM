import { useState } from "react";
import { COLORS } from "../../../constants/theme";
import { getThumbnailUrl } from "../../../utils/imageUtils";
import { TagIcon, ArrowRightIcon } from "../../../components/common/Icons";

const VideoCard = ({ video, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);

  if (!video) {
    return null;
  }

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onClick && video && video.id) {
      onClick(video);
    }
  };

  return (
    <div
      style={{ cursor: "pointer", position: "relative" }}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick(e);
        }
      }}
    >
      <div
        style={{
          width: "100%",
          aspectRatio: "16/10",
          backgroundColor: COLORS.lightGray,
          borderRadius: "12px",
          marginBottom: "12px",
          overflow: "hidden",
          position: "relative",
          backgroundImage: video.thumbnail_url
            ? `url(${getThumbnailUrl(video.thumbnail_url)})`
            : "none",
          backgroundSize: isHovered ? "110%" : "cover",
          backgroundPosition: "center",
          transform: isHovered ? "scale(1.03)" : "scale(1)",
          transition: "background-size 0.5s ease, transform 0.3s ease",
        }}
      >
        {/* 호버 시 하단 그라데이션 오버레이 */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "70%",
            background: isHovered
              ? `linear-gradient(to top, rgba(207, 253, 30, 0.3), rgba(194, 224, 246, 0.2), transparent)`
              : "transparent",
            transition: "opacity 0.3s ease, background 0.3s ease",
            pointerEvents: "none",
          }}
        />
      </div>
      <div
        style={{
          fontSize: "13px",
          color: COLORS.gray,
          marginBottom: "6px",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          flexWrap: "wrap",
        }}
      >
        {video.video_keyword && (
          <>
            {video.video_keyword.split(",").map((keyword, idx) => {
              const trimmedKeyword = keyword.trim();
              if (!trimmedKeyword) return null;
              return (
                <span
                  key={`keyword-${idx}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "2px",
                  }}
                >
                  <span>#{trimmedKeyword}</span>
                </span>
              );
            })}
          </>
        )}
        {video.tags && Array.isArray(video.tags) && video.tags.length > 0 ? (
          video.tags.map((tag, idx) => (
            <span
              key={idx}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <TagIcon size={12} color={COLORS.gray} />
              <span>{tag}</span>
            </span>
          ))
        ) : video.tags ? (
          <span>{video.tags}</span>
        ) : null}
      </div>
      <div
        style={{
          fontSize: "17px",
          fontWeight: "600",
          color: COLORS.dark,
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span>{video.title || ""}</span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            opacity: isHovered ? 1 : 0,
            transform: isHovered
              ? "translateX(0) rotate(-45deg)"
              : "translateX(-8px) rotate(-45deg)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
          }}
        >
          <ArrowRightIcon size={18} color={COLORS.dark} />
        </span>
      </div>
    </div>
  );
};

export default VideoCard;
