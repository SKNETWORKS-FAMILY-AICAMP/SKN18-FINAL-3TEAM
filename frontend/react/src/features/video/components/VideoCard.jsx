import { COLORS } from "../../../constants/theme";
import { getThumbnailUrl } from "../../../utils/imageUtils";
import { TagIcon } from "../../../components/common/Icons";

const VideoCard = ({ video, onClick }) => {
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
          transition: "transform 0.3s ease",
          overflow: "hidden",
          backgroundImage: video.thumbnail_url
            ? `url(${getThumbnailUrl(video.thumbnail_url)})`
            : "none",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.02)")}
        onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
      ></div>
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
            {video.video_keyword.split(',').map((keyword, idx) => {
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
        }}
      >
        {video.title || ""}
      </div>
    </div>
  );
};

export default VideoCard;
