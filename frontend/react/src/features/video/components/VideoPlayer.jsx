import { COLORS } from '../../../constants/theme';
import { PlayIcon } from '../../../components/common/Icons';

const VideoPlayer = () => {
  return (
    <div
      style={{
        width: '100%',
        aspectRatio: '16/9',
        backgroundColor: COLORS.lightGray,
        borderRadius: '16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <PlayIcon />
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          right: '20px',
          height: '6px',
          backgroundColor: 'rgba(0,0,0,0.2)',
          borderRadius: '3px',
        }}
      >
        <div
          style={{
            width: '25%',
            height: '100%',
            backgroundColor: COLORS.dark,
            borderRadius: '3px',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              right: '-8px',
              top: '50%',
              transform: 'translateY(-50%)',
              width: '16px',
              height: '16px',
              backgroundColor: COLORS.white,
              borderRadius: '50%',
              boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            }}
          ></div>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
