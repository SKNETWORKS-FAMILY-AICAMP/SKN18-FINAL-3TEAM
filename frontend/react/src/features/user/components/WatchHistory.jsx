import { COLORS } from "../../../constants/theme";
import { getThumbnailUrl } from "../../../utils/imageUtils";

const WatchHistory = ({ items, loading = false, onVideoClick }) => {
  return (
    <div style={{ width: "100%", maxWidth: "100%", overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "10px 20px",
            backgroundColor: COLORS.gray,
            borderRadius: "8px",
            color: COLORS.white,
            fontSize: "14px",
            fontWeight: "600",
          }}
        >
          내가 본 영상 기록
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: "20px",
          overflowX: "auto",
          overflowY: "hidden",
          paddingBottom: "20px",
          scrollbarWidth: "thin",
          scrollbarColor: `${COLORS.primary} ${COLORS.lightGray}`,
          WebkitOverflowScrolling: "touch",
          width: "100%",
        }}
        className="watch-history-scroll"
      >
        {loading ? (
          <div
            style={{ fontSize: "13px", color: COLORS.gray, padding: "20px" }}
          >
            로딩 중...
          </div>
        ) : items.length === 0 ? (
          <div
            style={{ fontSize: "13px", color: COLORS.gray, padding: "20px" }}
          >
            시청 기록이 없습니다.
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              style={{ minWidth: "140px", flexShrink: 0, cursor: "pointer" }}
              onClick={() => onVideoClick && onVideoClick(item.videoId)}
              className="video-thumbnail"
            >
              <div
                style={{
                  width: "140px",
                  height: "100px",
                  backgroundColor: COLORS.lightGray,
                  borderRadius: "8px",
                  marginBottom: "8px",
                  transition: "transform 0.2s ease, box-shadow 0.2s ease",
                  backgroundImage: item.thumbnail_url
                    ? `url(${getThumbnailUrl(item.thumbnail_url)})`
                    : "none",
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }}
              ></div>
              <div style={{ fontSize: "13px", color: COLORS.dark }}>
                {item.title}
              </div>
            </div>
          ))
        )}
      </div>

      <style>{`
        .watch-history-scroll {
          cursor: grab;
        }
        .watch-history-scroll:active {
          cursor: grabbing;
        }
        .watch-history-scroll::-webkit-scrollbar {
          height: 10px;
        }
        .watch-history-scroll::-webkit-scrollbar-track {
          background: ${COLORS.lightGray};
          border-radius: 5px;
          margin: 0 10px;
        }
        .watch-history-scroll::-webkit-scrollbar-thumb {
          background: ${COLORS.primary};
          border-radius: 5px;
          transition: background 0.2s ease;
        }
        .watch-history-scroll::-webkit-scrollbar-thumb:hover {
          background: ${COLORS.secondary};
        }
        .video-thumbnail:hover > div:first-child {
          transform: scale(1.05);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </div>
  );
};

export default WatchHistory;
