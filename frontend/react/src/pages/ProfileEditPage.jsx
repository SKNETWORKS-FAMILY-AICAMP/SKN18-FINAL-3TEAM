import { useState } from 'react';
import { COLORS } from '../constants/theme';
import { UserIcon, ArrowLeftIcon, CameraIcon } from '../components/common/Icons';

const ProfileEditPage = ({ onNavigate }) => {
  const [formData, setFormData] = useState({
    nickname: '사용자',
    email: 'user@example.com',
    bio: '역사를 좋아하는 사람입니다.'
  });

  return (
    <div style={{ padding: '50px 60px', backgroundColor: COLORS.bgMain, minHeight: 'calc(100vh - 88px)' }}>
      <button onClick={() => onNavigate('mypage')} style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        background: 'none', border: 'none', cursor: 'pointer',
        fontSize: '14px', color: COLORS.textSecondary, marginBottom: '40px',
      }}>
        <ArrowLeftIcon size={18} color={COLORS.textSecondary} />
        마이페이지로 돌아가기
      </button>

      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '800', color: COLORS.textPrimary, marginBottom: '50px' }}>프로필 수정</h1>

        <div style={{ textAlign: 'center', marginBottom: '50px' }}>
          <div style={{
            width: '140px', height: '140px', borderRadius: '50%',
            backgroundColor: COLORS.primary, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px', position: 'relative',
          }}>
            <UserIcon size={70} color={COLORS.textPrimary} />
            <button style={{
              position: 'absolute', bottom: '0', right: '0',
              width: '42px', height: '42px', borderRadius: '50%',
              backgroundColor: COLORS.cardCream, border: `3px solid ${COLORS.bgMain}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            }}>
              <CameraIcon size={20} color={COLORS.textPrimary} />
            </button>
          </div>
          <span style={{ fontSize: '13px', color: COLORS.textMuted }}>프로필 사진 변경</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {[
            { label: '닉네임', key: 'nickname', type: 'text' },
            { label: '이메일', key: 'email', type: 'email' },
          ].map((field) => (
            <div key={field.key}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, marginBottom: '10px' }}>{field.label}</label>
              <input type={field.type} value={formData[field.key]}
                onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                style={{
                  width: '100%', padding: '16px 20px',
                  border: 'none', borderRadius: '12px',
                  fontSize: '16px', backgroundColor: COLORS.cardCream,
                  color: COLORS.textPrimary, outline: 'none',
                }}
                onFocus={(e) => e.target.style.boxShadow = `0 0 0 3px ${COLORS.primary}`}
                onBlur={(e) => e.target.style.boxShadow = 'none'}
              />
            </div>
          ))}

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, marginBottom: '10px' }}>자기소개</label>
            <textarea value={formData.bio} onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
              rows={4} style={{
                width: '100%', padding: '16px 20px', border: 'none', borderRadius: '12px',
                fontSize: '16px', backgroundColor: COLORS.cardCream, color: COLORS.textPrimary,
                outline: 'none', resize: 'none', fontFamily: 'inherit',
              }}
              onFocus={(e) => e.target.style.boxShadow = `0 0 0 3px ${COLORS.primary}`}
              onBlur={(e) => e.target.style.boxShadow = 'none'}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, marginBottom: '12px' }}>관심 분야</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {[
                { tag: '전쟁사', active: true, color: COLORS.cardLime },
                { tag: '발명품', active: true, color: COLORS.cardSky },
                { tag: '왕실', active: false },
                { tag: '문화', active: false },
                { tag: '건축', active: false },
              ].map((item) => (
                <button key={item.tag} style={{
                  padding: '10px 20px', borderRadius: '25px',
                  border: item.active ? 'none' : `2px solid ${COLORS.border}`,
                  backgroundColor: item.active ? item.color : 'transparent',
                  color: COLORS.textPrimary, fontSize: '14px', fontWeight: '600', cursor: 'pointer',
                }}>
                  # {item.tag}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '16px', marginTop: '50px' }}>
          <button onClick={() => onNavigate('mypage')} style={{
            flex: 1, padding: '16px 28px', border: `2px solid ${COLORS.border}`,
            borderRadius: '12px', backgroundColor: 'transparent',
            fontSize: '16px', fontWeight: '600', cursor: 'pointer', color: COLORS.textSecondary,
          }}>취소</button>
          <button style={{
            flex: 1, padding: '16px 28px', border: 'none', borderRadius: '12px',
            backgroundColor: COLORS.primary, fontSize: '16px', fontWeight: '700',
            cursor: 'pointer', color: COLORS.textPrimary, transition: 'transform 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
          >저장하기</button>
        </div>
      </div>
    </div>
  );
};

export default ProfileEditPage;
