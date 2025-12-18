import { COLORS } from '../../../constants/theme';

const SuggestedVideos = ({ videos, searchValue, contentVisible }) => {
  return (
    <div style={{ flex: 1 }}>
      <h3
        style={{
          fontSize: '15px',
          fontWeight: '700',
          color: COLORS.dark,
          marginBottom: '20px',
          letterSpacing: '0.5px',
        }}
      >
        {searchValue ? `"${searchValue}" 관련 영상` : '추천 영상'}
      </h3>

      <div
        style={{
          display: 'flex',
          gap: '20px',
          overflowX: 'auto',
          paddingBottom: '20px',
        }}
      >
        {videos.map((video, idx) => (
          <div
            key={video.id}
            style={{
              minWidth: '180px',
              cursor: 'pointer',
              opacity: contentVisible ? 1 : 0,
              transform: contentVisible ? 'translateY(0)' : 'translateY(20px)',
              transition: `all 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${
                0.15 + idx * 0.05
              }s`,
            }}
          >
            <div
              style={{
                width: '180px',
                height: '220px',
                backgroundColor: COLORS.lightGray,
                borderRadius: '8px',
                marginBottom: '12px',
                overflow: 'hidden',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.03)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: `hsl(${idx * 30 + 200}, 20%, 90%)`,
                }}
              >
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#bbb"
                  strokeWidth="1.5"
                >
                  <polygon points="5,3 19,12 5,21" fill="#ddd" stroke="none" />
                </svg>
              </div>
            </div>
            <div
              style={{
                fontSize: '14px',
                fontWeight: '600',
                color: COLORS.dark,
                marginBottom: '4px',
                lineHeight: '1.4',
              }}
            >
              {video.title}
            </div>
            <div
              style={{
                fontSize: '12px',
                color: COLORS.gray,
              }}
            >
              {video.tags}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SuggestedVideos;
