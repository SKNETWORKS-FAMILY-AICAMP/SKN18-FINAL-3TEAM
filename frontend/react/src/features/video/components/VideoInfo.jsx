import { COLORS } from '../../../constants/theme';
import { HeartIcon } from '../../../components/common/Icons';

const VideoInfo = ({ tags, title, date, isLiked, onLikeClick }) => {
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
        <div style={{ fontSize: '13px', color: COLORS.gray, marginBottom: '8px' }}>
          {tags}
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
            color: '#e8a4b8',
            cursor: 'pointer',
          }}
        >
          <span>좋아요.</span>
          <HeartIcon filled={isLiked} />
        </div>
      </div>
    </div>
  );
};

export default VideoInfo;
