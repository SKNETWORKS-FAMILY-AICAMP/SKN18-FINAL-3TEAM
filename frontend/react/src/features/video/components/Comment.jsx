import { COLORS } from '../../../constants/theme';
import { UserIcon, HeartIcon } from '../../../components/common/Icons';

const Comment = ({ comment }) => {
  return (
    <div style={{ marginBottom: '20px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '8px',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: COLORS.lightGray,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <UserIcon size={16} />
        </div>
        <span style={{ fontSize: '13px', fontWeight: '600', color: COLORS.dark }}>
          {comment.username}
        </span>
      </div>
      <div
        style={{
          fontSize: '14px',
          color: COLORS.dark,
          lineHeight: '1.5',
          marginLeft: '42px',
        }}
      >
        {comment.text}
      </div>

      {comment.replies?.map((reply) => (
        <div
          key={reply.id}
          style={{
            marginLeft: '20px',
            marginTop: '12px',
            position: 'relative',
            paddingLeft: '22px',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: '0',
              top: '-8px',
              width: '16px',
              height: '28px',
              borderLeft: '2px solid #ddd',
              borderBottom: '2px solid #ddd',
              borderBottomLeftRadius: '12px',
            }}
          ></div>

          <div
            style={{
              backgroundColor: '#f8f8f8',
              borderRadius: '12px',
              padding: '12px 16px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '6px',
              }}
            >
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: reply.isAI ? COLORS.primary : COLORS.lightGray,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {reply.isAI ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <circle cx="10" cy="10" r="6" fill="#c8e0ff" />
                    <path
                      d="M14 8c5 0 7 3 7 6s-2 8-6 8-5-3-5-6"
                      fill={COLORS.primary}
                    />
                  </svg>
                ) : (
                  <UserIcon size={12} />
                )}
              </div>
              <span style={{ fontSize: '12px', fontWeight: '600', color: COLORS.dark }}>
                {reply.username}
              </span>
            </div>
            <div style={{ fontSize: '13px', color: COLORS.dark, lineHeight: '1.5' }}>
              {reply.text}
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                marginTop: '8px',
                fontSize: '12px',
                color: '#999',
              }}
            >
              <span>좋아요</span>
              <HeartIcon filled={false} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Comment;
