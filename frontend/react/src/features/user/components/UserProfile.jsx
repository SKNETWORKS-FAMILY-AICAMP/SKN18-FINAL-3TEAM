import { COLORS } from '../../../constants/theme';
import { UserIcon } from '../../../components/common/Icons';

const UserProfile = ({ onEdit }) => {
  return (
    <div style={{ width: '200px', textAlign: 'center' }}>
      <div
        style={{
          width: '160px',
          height: '160px',
          borderRadius: '50%',
          backgroundColor: COLORS.primary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
        }}
      >
        <UserIcon size={80} />
      </div>
      <button
        onClick={onEdit}
        style={{
          padding: '10px 24px',
          border: '2px solid #333',
          borderRadius: '8px',
          backgroundColor: 'transparent',
          fontSize: '14px',
          fontWeight: '600',
          cursor: 'pointer',
        }}
      >
        수정하기
      </button>
    </div>
  );
};

export default UserProfile;
