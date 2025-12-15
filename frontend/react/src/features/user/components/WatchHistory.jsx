import { COLORS } from "../../../constants/theme";

const WatchHistory = ({ items, loading = false }) => {
  return (
    <div>
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
          paddingBottom: "20px",
          scrollbarWidth: "thin",
          scrollbarColor: `${COLORS.primary} ${COLORS.lightGray}`,
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
            <div key={item.id} style={{ minWidth: "140px", flexShrink: 0 }}>
              <div
                style={{
                  width: "140px",
                  height: "100px",
                  backgroundColor: COLORS.lightGray,
                  borderRadius: "8px",
                  marginBottom: "8px",
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
        .watch-history-scroll::-webkit-scrollbar {
          height: 8px;
        }
        .watch-history-scroll::-webkit-scrollbar-track {
          background: ${COLORS.lightGray};
          border-radius: 4px;
        }
        .watch-history-scroll::-webkit-scrollbar-thumb {
          background: ${COLORS.primary};
          border-radius: 4px;
        }
        .watch-history-scroll::-webkit-scrollbar-thumb:hover {
          background: ${COLORS.secondary};
        }
      `}</style>
    </div>
  );
};

export default WatchHistory;
