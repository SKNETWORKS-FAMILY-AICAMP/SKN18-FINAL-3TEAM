import { COLORS } from '../../../constants/theme';

const VideoCard = ({ video, onClick }) => {
  return (
    <div style={{ cursor: 'pointer' }} onClick={() => onClick(video)}>
      <div
        style={{
          width: '100%',
          aspectRatio: '16/10',
          backgroundColor: COLORS.lightGray,
          borderRadius: '12px',
          marginBottom: '12px',
          transition: 'transform 0.3s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      ></div>
      <div
        style={{
          fontSize: '13px',
          color: COLORS.gray,
          marginBottom: '6px',
        }}
      >
        {video.tags}
      </div>
      <div
        style={{
          fontSize: '17px',
          fontWeight: '600',
          color: COLORS.dark,
        }}
      >
        {video.title}
      </div>
    </div>
  );
};

export default VideoCard;
