import { COLORS } from '../../../constants/theme';
import { HeartIcon, TagIcon } from '../../../components/common/Icons';

const VideoInfo = ({ tags, title, date, isLiked, onLikeClick, likesCount = 0, video_keyword }) => {
  return (
    <div
      style={{
        marginTop: '16px',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
      }}
    >
      <div>
        <div
          style={{
            fontSize: '13px',
            color: COLORS.gray,
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            flexWrap: 'wrap',
          }}
        >
          {video_keyword && (
            <>
              {video_keyword.split(',').map((keyword, idx) => {
                const trimmedKeyword = keyword.trim();
                if (!trimmedKeyword) return null;
                return (
                  <span
                    key={`keyword-${idx}`}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '2px',
                    }}
                  >
                    <span>#{trimmedKeyword}</span>
                  </span>
                );
              })}
            </>
          )}
          {tags && typeof tags === 'string' ? (
            // 문자열로 전달된 경우 (기존 형식 호환)
            tags.split(' ').map((tagItem, idx) => {
              const tagText = tagItem.replace('#', '').trim();
              if (!tagText) return null;
              return (
                <span
                  key={idx}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <TagIcon size={12} color={COLORS.gray} />
                  <span>{tagText}</span>
                </span>
              );
            })
          ) : Array.isArray(tags) && tags.length > 0 ? (
            // 배열로 전달된 경우
            tags.map((tag, idx) => (
              <span
                key={idx}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <TagIcon size={12} color={COLORS.gray} />
                <span>{tag}</span>
              </span>
            ))
          ) : null}
        </div>
        <div style={{ fontSize: '24px', fontWeight: '700', color: COLORS.dark }}>
          {title}
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          fontSize: '14px',
          color: COLORS.gray,
        }}
      >
        <span>게시일 | {date}</span>
        <div
          onClick={onLikeClick}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: '#ff1493',
            cursor: 'pointer',
          }}
        >
          <span>좋아요 {likesCount}</span>
          <HeartIcon filled={isLiked} />
        </div>
      </div>
    </div>
  );
};

export default VideoInfo;
