import React, { useState, useEffect, useRef } from 'react';

// Fabian Molina 실제 색상 팔레트
const COLORS = {
  // 배경 (세이지 그린/베이지 톤)
  bgMain: '#c9c6bd',           // 메인 배경 (세이지 베이지)
  bgDark: '#b8b5ac',           // 어두운 배경
  
  // 카드 색상들
  cardCream: '#f0ede4',        // 크림/베이지 카드
  cardLime: '#d4f73f',         // 라임/연두 카드 (포인트)
  cardSky: '#c4dff0',          // 하늘색 카드
  cardWhite: '#f8f6f0',        // 흰색 카드
  
  // 포인트 & 태그
  primary: '#d4f73f',          // 메인 포인트 (라임)
  tag: '#7286ff',              // 태그 색상 (보라)
  sky: '#c4dff0',              // 하늘색
  
  // 텍스트
  textPrimary: '#1a1815',      // 메인 텍스트 (거의 검정)
  textSecondary: '#4a4740',    // 보조 텍스트
  textMuted: '#7a756d',        // 흐린 텍스트
  
  // 기타
  border: '#d5d2c9',
  white: '#ffffff',
  overlay: 'rgba(42, 40, 35, 0.92)',
};

// 전역 스타일
const GlobalStyles = () => (
  <style>{`
    ::selection {
      background-color: ${COLORS.primary};
      color: ${COLORS.textPrimary};
    }
    ::-moz-selection {
      background-color: ${COLORS.primary};
      color: ${COLORS.textPrimary};
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      background-color: ${COLORS.bgMain};
    }
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    ::-webkit-scrollbar-track {
      background: ${COLORS.bgDark};
    }
    ::-webkit-scrollbar-thumb {
      background: ${COLORS.border};
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: ${COLORS.textMuted};
    }
  `}</style>
);

// ========== 아이콘 컴포넌트들 ==========
const LogoIcon = ({ size = 48 }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    <circle cx="18" cy="18" r="14" fill={COLORS.sky} />
    <path d="M28 12 C38 12, 42 20, 42 28 C42 36, 36 42, 28 42 C20 42, 18 38, 18 32" 
          fill={COLORS.primary} stroke="none"/>
    <circle cx="28" cy="42" r="5" fill={COLORS.textPrimary} />
  </svg>
);

const SearchIcon = ({ color = COLORS.textPrimary, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
);

const UserIcon = ({ size = 20, color = COLORS.textPrimary }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <circle cx="12" cy="8" r="4"/>
    <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>
  </svg>
);

const PlayIcon = ({ size = 80 }) => (
  <svg width={size} height={size} viewBox="0 0 80 80" fill="none">
    <polygon points="30,20 30,60 60,40" fill={COLORS.textPrimary}/>
  </svg>
);

const HeartIcon = ({ filled, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" 
       fill={filled ? "#e07a7a" : "none"} 
       stroke="#e07a7a" strokeWidth="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
);

const CloseIcon = ({ size = 24, color = COLORS.textPrimary }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <path d="M18 6L6 18M6 6l12 12"/>
  </svg>
);

const PlusIcon = ({ size = 24, color = COLORS.textPrimary }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
    <path d="M12 5v14M5 12h14"/>
  </svg>
);

const ArrowLeftIcon = ({ size = 20, color = COLORS.textPrimary }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <path d="M19 12H5M12 19l-7-7 7-7"/>
  </svg>
);

const CameraIcon = ({ size = 24, color = COLORS.textPrimary }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
    <circle cx="12" cy="13" r="4"/>
  </svg>
);

// ========== 확장형 검색 컴포넌트 ==========
const ExpandableSearch = ({ isOpen, onClose }) => {
  const [searchValue, setSearchValue] = useState('');
  const [phase, setPhase] = useState(0);
  const inputRef = useRef(null);

  const searchHistory = ['연평도에서 발생한 사건', '조선의 발명품', '임진왜란'];
  const tags = ['# 발명품', '# 전쟁사', '# 세종', '# 정조', '# 양반', '# 과거제도', '# 한글', '# 실록'];
  const suggestedVideos = [
    { id: 1, title: '세종대왕의 한글 창제', tags: '#발명품 #세종' },
    { id: 2, title: '임진왜란의 전개 과정', tags: '#전쟁사 #선조' },
    { id: 3, title: '정조의 화성 건설', tags: '#건축 #정조' },
    { id: 4, title: '조선시대 과거제도', tags: '#제도 #양반' },
    { id: 5, title: '훈민정음 해례본', tags: '#발명품 #세종' },
  ];

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      setPhase(1);
      setTimeout(() => setPhase(2), 250);
      setTimeout(() => { setPhase(3); inputRef.current?.focus(); }, 500);
    } else {
      setPhase(2);
      setTimeout(() => setPhase(1), 150);
      setTimeout(() => { setPhase(0); document.body.style.overflow = ''; }, 350);
    }
  }, [isOpen]);

  if (phase === 0 && !isOpen) return null;

  const cardColors = [COLORS.cardCream, COLORS.cardLime, COLORS.cardSky];

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, pointerEvents: phase >= 1 ? 'auto' : 'none' }}>
      <div onClick={onClose} style={{
        position: 'absolute', inset: 0,
        backgroundColor: 'rgba(26, 24, 21, 0.5)',
        opacity: phase >= 1 ? 1 : 0,
        transition: 'opacity 0.3s ease',
      }} />
      
      <div style={{
        position: 'absolute', top: '20px', left: '50%',
        transform: 'translateX(-50%)',
        width: phase >= 1 ? 'calc(100% - 48px)' : '600px',
        maxWidth: '1400px',
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        <div style={{
          backgroundColor: COLORS.cardCream,
          borderRadius: '20px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.2)',
          overflow: 'hidden',
          maxHeight: phase >= 2 ? '520px' : '60px',
          transition: 'max-height 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center',
            padding: '0 28px', height: '60px',
            borderBottom: phase >= 2 ? `1px solid ${COLORS.border}` : 'none',
          }}>
            <span style={{ fontSize: '16px', fontWeight: '700', color: COLORS.textPrimary, marginRight: '20px' }}>검색</span>
            <SearchIcon color={COLORS.textMuted} />
            <input ref={inputRef} type="text" value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="검색어를 입력하세요"
              style={{
                flex: 1, border: 'none', outline: 'none',
                fontSize: '16px', backgroundColor: 'transparent',
                color: COLORS.textPrimary, marginLeft: '12px',
              }}
            />
            <button onClick={() => setSearchValue('')} style={{
              background: 'none', border: 'none', fontSize: '14px',
              color: COLORS.textSecondary, cursor: 'pointer', padding: '8px 16px',
            }}>초기화</button>
            <button onClick={onClose} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '8px', display: 'flex', alignItems: 'center',
            }}>
              <CloseIcon size={22} color={COLORS.textSecondary} />
            </button>
          </div>

          <div style={{
            display: 'flex', padding: '32px', gap: '48px',
            opacity: phase >= 3 ? 1 : 0,
            transform: phase >= 3 ? 'translateY(0)' : 'translateY(-10px)',
            transition: 'all 0.3s ease 0.1s',
          }}>
            <div style={{ flex: '0 0 320px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, marginBottom: '16px' }}>검색 기록</h3>
              <div>
                {searchHistory.map((item, idx) => (
                  <div key={idx} onClick={() => setSearchValue(item)} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 0', borderBottom: `1px solid ${COLORS.border}`,
                    cursor: 'pointer',
                    opacity: phase >= 3 ? 1 : 0,
                    transform: phase >= 3 ? 'translateX(0)' : 'translateX(-15px)',
                    transition: `all 0.3s ease ${0.15 + idx * 0.05}s`,
                  }}>
                    <span style={{ fontSize: '14px', color: COLORS.textSecondary }}>{item}</span>
                    <CloseIcon size={14} color={COLORS.textMuted} />
                  </div>
                ))}
              </div>
              
              <h3 style={{ fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, margin: '28px 0 16px' }}>인기 태그</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {tags.map((tag, idx) => (
                  <button key={idx} onClick={() => setSearchValue(tag.replace('# ', ''))}
                    style={{
                      padding: '10px 18px', backgroundColor: 'transparent',
                      border: `2px solid ${COLORS.tag}`, borderRadius: '25px',
                      color: COLORS.tag, fontSize: '13px', fontWeight: '600',
                      cursor: 'pointer', transition: 'all 0.2s ease',
                      opacity: phase >= 3 ? 1 : 0,
                      transform: phase >= 3 ? 'translateY(0)' : 'translateY(8px)',
                      transitionDelay: `${0.2 + idx * 0.025}s`,
                    }}
                    onMouseEnter={(e) => { e.target.style.backgroundColor = COLORS.tag; e.target.style.color = COLORS.white; }}
                    onMouseLeave={(e) => { e.target.style.backgroundColor = 'transparent'; e.target.style.color = COLORS.tag; }}
                  >{tag}</button>
                ))}
              </div>
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <h3 style={{ fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary, marginBottom: '16px' }}>
                {searchValue ? `"${searchValue}" 관련 영상` : '추천 영상'}
              </h3>
              <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '8px' }}>
                {suggestedVideos.map((video, idx) => (
                  <div key={video.id} style={{
                    minWidth: '150px', cursor: 'pointer',
                    opacity: phase >= 3 ? 1 : 0,
                    transform: phase >= 3 ? 'translateY(0)' : 'translateY(15px)',
                    transition: `all 0.3s ease ${0.2 + idx * 0.04}s`,
                  }}>
                    <div style={{
                      width: '150px', height: '190px',
                      backgroundColor: cardColors[idx % 3],
                      borderRadius: '12px', marginBottom: '12px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'transform 0.25s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.03)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                    >
                      <PlusIcon size={28} color={COLORS.textPrimary} />
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: '600', color: COLORS.textPrimary, marginBottom: '4px' }}>{video.title}</div>
                    <div style={{ fontSize: '12px', color: COLORS.textMuted }}>{video.tags}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ padding: '0 32px 24px', opacity: phase >= 3 ? 0.6 : 0, transition: 'opacity 0.3s ease 0.3s' }}>
            <LogoIcon size={40} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 헤더 컴포넌트 ==========
const Header = ({ isLoggedIn, showUserDropdown, setShowUserDropdown, onSearchClick, onNavigate }) => (
  <header style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 60px', backgroundColor: COLORS.cardCream,
    borderBottom: `1px solid ${COLORS.border}`,
  }}>
    <div onClick={() => onNavigate('main')} style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
      <LogoIcon size={44} />
      <div style={{ fontSize: '14px', fontWeight: '700', lineHeight: '1.3', color: COLORS.textPrimary }}>
        History &<br />Contents
      </div>
    </div>
    
    <div onClick={onSearchClick} style={{ flex: 1, maxWidth: '600px', margin: '0 40px', cursor: 'pointer' }}>
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '14px 20px', backgroundColor: COLORS.bgMain,
        borderRadius: '35px', transition: 'all 0.3s ease',
      }}
      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = COLORS.bgDark}
      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = COLORS.bgMain}
      >
        <SearchIcon color={COLORS.textMuted} size={18} />
        <span style={{ marginLeft: '12px', fontSize: '15px', color: COLORS.textMuted }}>검색어를 입력하세요</span>
        <div style={{
          marginLeft: 'auto', width: '36px', height: '36px',
          borderRadius: '50%', backgroundColor: COLORS.primary,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <SearchIcon color={COLORS.textPrimary} size={16} />
        </div>
      </div>
    </div>
    
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ display: 'flex', backgroundColor: COLORS.bgMain, borderRadius: '8px', overflow: 'hidden' }}>
        <button style={{ padding: '10px 16px', border: 'none', backgroundColor: COLORS.cardCream, fontSize: '13px', cursor: 'pointer', fontWeight: '600', color: COLORS.textPrimary }}>한</button>
        <button style={{ padding: '10px 16px', border: 'none', backgroundColor: 'transparent', fontSize: '13px', cursor: 'pointer', fontWeight: '500', color: COLORS.textSecondary }}>EN</button>
      </div>
      
      <div style={{ position: 'relative' }}>
        <button onClick={() => setShowUserDropdown(!showUserDropdown)} style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '8px 16px', backgroundColor: 'transparent',
          border: 'none', cursor: 'pointer',
        }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '50%',
            backgroundColor: COLORS.primary, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <UserIcon color={COLORS.textPrimary} size={20} />
          </div>
          <span style={{ fontSize: '15px', fontWeight: '600', color: COLORS.textPrimary }}>{isLoggedIn ? '사용자' : '로그인'}</span>
        </button>
        
        {isLoggedIn && showUserDropdown && (
          <div style={{
            position: 'absolute', top: '55px', right: '0',
            backgroundColor: COLORS.overlay, borderRadius: '14px',
            padding: '8px 0', minWidth: '150px', zIndex: 1000,
          }}>
            <div onClick={() => { onNavigate('mypage'); setShowUserDropdown(false); }}
                 style={{ padding: '14px 24px', color: COLORS.primary, fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}>나의 기록</div>
            <div style={{ padding: '14px 24px', color: COLORS.primary, fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}>→ 로그아웃</div>
          </div>
        )}
      </div>
    </div>
  </header>
);

// ========== 메인 페이지 (Fabian Molina 스타일 카드) ==========
const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const videos = [
    { id: 1, tags: '#전쟁사 #정조', title: '정조의 군사 개혁', date: 'Dec 10, 24', color: COLORS.cardCream },
    { id: 2, tags: '#발명품 #세종', title: '해시계 앙부일구', date: 'Nov 28, 24', color: COLORS.cardLime },
    { id: 3, tags: '#건축 #정조', title: '수원 화성 축조', date: 'Nov 15, 24', color: COLORS.cardSky },
    { id: 4, tags: '#문화 #세종', title: '집현전의 학자들', date: 'Oct 22, 24', color: COLORS.cardCream },
    { id: 5, tags: '#전쟁사 #선조', title: '임진왜란 해전', date: 'Oct 10, 24', color: COLORS.cardLime },
    { id: 6, tags: '#발명품 #장영실', title: '자격루의 원리', date: 'Sep 18, 24', color: COLORS.cardSky },
  ];

  return (
    <main style={{ padding: '50px 60px', backgroundColor: COLORS.bgMain, minHeight: 'calc(100vh - 88px)' }}>
      {/* 타이틀 섹션 */}
      <div style={{ marginBottom: '50px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '20px', marginBottom: '8px' }}>
          <h1 style={{ fontSize: '48px', fontWeight: '800', color: COLORS.textPrimary, letterSpacing: '-1px' }}>
            {isLoggedIn ? '추천 영상' : '인기 영상'}
          </h1>
          <span style={{ fontSize: '18px', color: COLORS.textMuted }}>2024 - 2025</span>
        </div>
      </div>
      
      {/* 카드 리스트 (Fabian Molina 스타일) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '900px' }}>
        {videos.map((video, idx) => (
          <div key={video.id} onClick={() => onVideoClick(video)} style={{
            display: 'flex', alignItems: 'center',
            padding: '24px 32px',
            backgroundColor: video.color,
            borderRadius: '16px',
            cursor: 'pointer',
            transition: 'transform 0.2s ease, box-shadow 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateX(8px)';
            e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateX(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
          >
            <PlusIcon size={24} color={COLORS.textPrimary} />
            <div style={{ flex: 1, marginLeft: '20px' }}>
              <span style={{ fontSize: '22px', fontWeight: '700', color: COLORS.textPrimary }}>{video.title}</span>
            </div>
            <span style={{ fontSize: '14px', fontWeight: '500', color: COLORS.textSecondary }}>{video.date}</span>
          </div>
        ))}
      </div>
    </main>
  );
};

// ========== 비디오 상세 페이지 ==========
const VideoDetailPage = ({ onNavigate }) => {
  const comments = [
    { id: 1, username: '역사탐험가', text: '해당 사건은 몇년도에 발생하였나요?',
      replies: [{ id: 11, username: 'AI 답변', text: '해당 사건은 1425년(세종 7년)에 발생한 사건입니다.', isAI: true }] },
    { id: 2, username: '조선덕후', text: '영상이 정말 마음에 들어요', replies: [] },
    { id: 3, username: '학생123', text: '과제 하는데 도움이 많이 됐습니다!', replies: [] },
  ];

  return (
    <div style={{ display: 'flex', gap: '30px', padding: '40px 60px', backgroundColor: COLORS.bgMain, minHeight: 'calc(100vh - 88px)' }}>
      <div style={{ flex: 1 }}>
        <div style={{
          width: '100%', aspectRatio: '16/9',
          backgroundColor: COLORS.cardCream, borderRadius: '20px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative',
        }}>
          <PlayIcon size={80} />
          <div style={{
            position: 'absolute', bottom: '24px', left: '24px', right: '24px',
            height: '6px', backgroundColor: COLORS.bgDark, borderRadius: '3px',
          }}>
            <div style={{ width: '25%', height: '100%', backgroundColor: COLORS.textPrimary, borderRadius: '3px', position: 'relative' }}>
              <div style={{
                position: 'absolute', right: '-8px', top: '50%', transform: 'translateY(-50%)',
                width: '18px', height: '18px', backgroundColor: COLORS.cardWhite,
                borderRadius: '50%', boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              }} />
            </div>
          </div>
        </div>
        
        <div style={{ marginTop: '20px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '13px', color: COLORS.textMuted, marginBottom: '8px' }}>#전쟁사 #정조</div>
            <div style={{ fontSize: '28px', fontWeight: '700', color: COLORS.textPrimary }}>정조의 군사 개혁</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px', fontSize: '14px', color: COLORS.textSecondary }}>
            <span>게시일 | 2025. 12. 01.</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <span>좋아요</span>
              <HeartIcon filled={false} />
            </div>
          </div>
        </div>
      </div>
      
      {/* 댓글 섹션 */}
      <div style={{
        width: '400px', backgroundColor: COLORS.cardCream,
        borderRadius: '20px', display: 'flex', flexDirection: 'column', maxHeight: '650px',
      }}>
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
          {comments.map((comment) => (
            <div key={comment.id} style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  backgroundColor: COLORS.bgMain, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <UserIcon size={18} color={COLORS.textSecondary} />
                </div>
                <span style={{ fontSize: '14px', fontWeight: '700', color: COLORS.textPrimary }}>{comment.username}</span>
              </div>
              <div style={{ fontSize: '15px', color: COLORS.textPrimary, lineHeight: '1.5', marginLeft: '48px' }}>{comment.text}</div>
              
              {comment.replies.map((reply) => (
                <div key={reply.id} style={{ marginLeft: '24px', marginTop: '16px', position: 'relative', paddingLeft: '24px' }}>
                  <div style={{
                    position: 'absolute', left: '0', top: '-10px',
                    width: '18px', height: '32px',
                    borderLeft: `2px solid ${COLORS.border}`,
                    borderBottom: `2px solid ${COLORS.border}`,
                    borderBottomLeftRadius: '14px',
                  }} />
                  <div style={{ backgroundColor: COLORS.cardSky, borderRadius: '14px', padding: '14px 18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <div style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        backgroundColor: COLORS.primary, display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                      }}>
                        <LogoIcon size={16} />
                      </div>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textPrimary }}>{reply.username}</span>
                    </div>
                    <div style={{ fontSize: '14px', color: COLORS.textPrimary, lineHeight: '1.5' }}>{reply.text}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', fontSize: '12px', color: COLORS.textMuted }}>
                      <span>좋아요</span>
                      <HeartIcon filled={false} size={14} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
        
        <div style={{ padding: '20px 24px', borderTop: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: '14px', fontWeight: '700', marginBottom: '14px', color: COLORS.textPrimary }}>댓글 작성하기</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '50%',
              backgroundColor: COLORS.primary, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
            }}>
              <UserIcon size={18} color={COLORS.textPrimary} />
            </div>
            <input type="text" placeholder="댓글을 입력하세요..." style={{
              flex: 1, padding: '14px 18px',
              border: 'none', borderRadius: '12px',
              fontSize: '14px', backgroundColor: COLORS.bgMain,
              color: COLORS.textPrimary, outline: 'none',
            }} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 마이페이지 ==========
const MyPage = ({ onNavigate }) => {
  const watchHistory = [
    { id: 1, title: '정조의 군사 개혁', color: COLORS.cardLime },
    { id: 2, title: '해시계 앙부일구', color: COLORS.cardSky },
    { id: 3, title: '수원 화성 축조', color: COLORS.cardCream },
    { id: 4, title: '집현전의 학자들', color: COLORS.cardLime },
  ];

  return (
    <div style={{ display: 'flex', gap: '50px', padding: '50px 60px', backgroundColor: COLORS.bgMain, minHeight: 'calc(100vh - 88px)' }}>
      <div style={{ width: '220px', textAlign: 'center' }}>
        <div style={{
          width: '180px', height: '180px', borderRadius: '50%',
          backgroundColor: COLORS.primary, display: 'flex',
          alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
        }}>
          <UserIcon size={90} color={COLORS.textPrimary} />
        </div>
        <button onClick={() => onNavigate('profile-edit')} style={{
          padding: '14px 28px', border: `2px solid ${COLORS.textPrimary}`,
          borderRadius: '10px', backgroundColor: 'transparent',
          fontSize: '15px', fontWeight: '700', cursor: 'pointer',
          color: COLORS.textPrimary, transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = COLORS.textPrimary; e.currentTarget.style.color = COLORS.cardCream; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = COLORS.textPrimary; }}
        >수정하기</button>
      </div>
      
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'inline-block', padding: '12px 24px',
          backgroundColor: COLORS.cardLime, borderRadius: '10px',
          fontSize: '15px', fontWeight: '700', marginBottom: '24px',
          color: COLORS.textPrimary,
        }}>내가 본 영상 기록</div>
        
        <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '24px' }}>
          {watchHistory.map((item) => (
            <div key={item.id} style={{ minWidth: '160px', cursor: 'pointer' }}>
              <div style={{
                width: '160px', height: '120px',
                backgroundColor: item.color, borderRadius: '12px',
                marginBottom: '10px', display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                transition: 'transform 0.2s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.03)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                <PlusIcon size={24} color={COLORS.textPrimary} />
              </div>
              <div style={{ fontSize: '14px', fontWeight: '600', color: COLORS.textPrimary }}>{item.title}</div>
            </div>
          ))}
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginTop: '40px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
              <div style={{
                padding: '12px 24px', backgroundColor: COLORS.cardSky,
                borderRadius: '10px', fontSize: '15px', fontWeight: '700', color: COLORS.textPrimary,
              }}>내가 남긴 댓글</div>
              <button onClick={() => onNavigate('all-comments')} style={{
                padding: '10px 20px', border: `2px solid ${COLORS.textPrimary}`,
                borderRadius: '8px', backgroundColor: 'transparent',
                fontSize: '13px', fontWeight: '600', cursor: 'pointer', color: COLORS.textPrimary,
              }}>전체보기</button>
            </div>
            <div style={{ backgroundColor: COLORS.cardCream, borderRadius: '16px', padding: '24px' }}>
              <div style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px', color: COLORS.textPrimary }}>정조의 군사 개혁</div>
              <div style={{ marginLeft: '12px' }}>
                <div style={{ fontSize: '14px', color: COLORS.textSecondary, position: 'relative', paddingLeft: '18px', marginBottom: '8px' }}>
                  <div style={{
                    position: 'absolute', left: '0', top: '0', width: '12px', height: '100%',
                    borderLeft: `2px solid ${COLORS.border}`, borderBottom: `2px solid ${COLORS.border}`,
                    borderBottomLeftRadius: '10px',
                  }} />
                  해당 사건은 몇년도에 발생하였나요?
                </div>
                <div style={{ fontSize: '14px', color: COLORS.textSecondary, position: 'relative', paddingLeft: '18px', marginLeft: '18px' }}>
                  <div style={{
                    position: 'absolute', left: '0', top: '0', width: '12px', height: '100%',
                    borderLeft: `2px solid ${COLORS.border}`, borderBottom: `2px solid ${COLORS.border}`,
                    borderBottomLeftRadius: '10px',
                  }} />
                  해당 사건은 1425년(세종 7년)에 발생한 사건입니다.
                </div>
              </div>
            </div>
          </div>
          
          <div>
            <div style={{
              padding: '12px 24px', backgroundColor: COLORS.primary,
              borderRadius: '10px', fontSize: '15px', fontWeight: '700',
              color: COLORS.textPrimary, marginBottom: '20px', display: 'inline-block',
            }}>기록 분석</div>
            <div style={{ backgroundColor: COLORS.cardCream, borderRadius: '16px', padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '30px' }}>
                <svg width="140" height="140" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill={COLORS.primary} />
                  <path d="M50 50 L50 10 A40 40 0 0 1 90 50 Z" fill={COLORS.tag} />
                  <path d="M50 50 L90 50 A40 40 0 0 1 70 85 Z" fill={COLORS.cardSky} />
                  <path d="M50 50 L70 85 A40 40 0 0 1 30 85 Z" fill={COLORS.textMuted} />
                </svg>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {[{ w: 100, c: COLORS.primary }, { w: 70, c: COLORS.tag }, { w: 45, c: COLORS.cardSky }, { w: 25, c: COLORS.textMuted }].map((bar, i) => (
                    <div key={i} style={{ height: '14px', borderRadius: '7px', width: `${bar.w}%`, backgroundColor: bar.c }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 프로필 수정 페이지 ==========
const ProfileEditPage = ({ onNavigate }) => {
  const [formData, setFormData] = useState({ nickname: '사용자', email: 'user@example.com', bio: '역사를 좋아하는 사람입니다.' });

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

// ========== 댓글 전체 보기 페이지 ==========
const AllCommentsPage = ({ onNavigate }) => {
  const allComments = [
    { id: 1, videoTitle: '정조의 군사 개혁', date: '2025.12.10', comment: '해당 사건은 몇년도에 발생하였나요?',
      reply: { text: '해당 사건은 1425년(세종 7년)에 발생한 사건입니다.' }, color: COLORS.cardCream },
    { id: 2, videoTitle: '해시계 앙부일구', date: '2025.12.08', comment: '앙부일구의 작동 원리가 궁금합니다.',
      reply: { text: '앙부일구는 해의 그림자를 이용해 시간을 측정하는 해시계입니다.' }, color: COLORS.cardLime },
    { id: 3, videoTitle: '수원 화성 축조', date: '2025.12.05', comment: '화성 축조에 걸린 기간이 얼마나 되나요?', reply: null, color: COLORS.cardSky },
    { id: 4, videoTitle: '임진왜란 해전', date: '2025.12.01', comment: '이순신 장군의 전략이 정말 대단하네요!', reply: null, color: COLORS.cardCream },
    { id: 5, videoTitle: '집현전의 학자들', date: '2025.11.28', comment: '집현전에서 가장 유명한 학자는 누구인가요?',
      reply: { text: '정인지, 성삼문, 신숙주 등이 대표적인 집현전 학자입니다.' }, color: COLORS.cardLime },
  ];

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

      <div style={{ maxWidth: '900px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '40px' }}>
          <h1 style={{ fontSize: '32px', fontWeight: '800', color: COLORS.textPrimary }}>내가 남긴 댓글</h1>
          <span style={{
            padding: '8px 18px', borderRadius: '25px',
            backgroundColor: COLORS.primary, fontSize: '15px',
            fontWeight: '700', color: COLORS.textPrimary,
          }}>{allComments.length}개</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {allComments.map((item, idx) => (
            <div key={item.id} style={{
              backgroundColor: item.color, borderRadius: '20px', padding: '28px',
              cursor: 'pointer', transition: 'transform 0.2s',
              animation: `fadeIn 0.4s ease ${idx * 0.05}s both`,
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateX(8px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateX(0)'}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <PlusIcon size={20} color={COLORS.textPrimary} />
                  <span style={{ fontSize: '18px', fontWeight: '700', color: COLORS.textPrimary }}>{item.videoTitle}</span>
                </div>
                <span style={{ fontSize: '14px', color: COLORS.textMuted }}>{item.date}</span>
              </div>

              <div style={{
                backgroundColor: 'rgba(255,255,255,0.5)', borderRadius: '12px',
                padding: '16px 20px', marginBottom: item.reply ? '12px' : 0,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <div style={{
                    width: '26px', height: '26px', borderRadius: '50%',
                    backgroundColor: COLORS.primary, display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <UserIcon size={14} color={COLORS.textPrimary} />
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textPrimary }}>나</span>
                </div>
                <p style={{ fontSize: '15px', color: COLORS.textPrimary, margin: 0, lineHeight: '1.5' }}>{item.comment}</p>
              </div>

              {item.reply && (
                <div style={{ position: 'relative', paddingLeft: '24px' }}>
                  <div style={{
                    position: 'absolute', left: '10px', top: '-8px',
                    width: '14px', height: '28px',
                    borderLeft: `2px solid ${COLORS.border}`,
                    borderBottom: `2px solid ${COLORS.border}`,
                    borderBottomLeftRadius: '12px',
                  }} />
                  <div style={{ backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: '12px', padding: '16px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <div style={{
                        width: '26px', height: '26px', borderRadius: '50%',
                        backgroundColor: COLORS.cardSky, display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                      }}>
                        <LogoIcon size={14} />
                      </div>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textPrimary }}>AI 답변</span>
                    </div>
                    <p style={{ fontSize: '15px', color: COLORS.textPrimary, margin: 0, lineHeight: '1.5' }}>{item.reply.text}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(15px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

// ========== 메인 앱 ==========
const HistoryContentsApp = () => {
  const [currentPage, setCurrentPage] = useState('main');
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const handleNavigate = (page) => { setCurrentPage(page); setShowUserDropdown(false); };

  return (
    <div style={{
      fontFamily: "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
      backgroundColor: COLORS.bgMain, minHeight: '100vh', color: COLORS.textPrimary,
    }}>
      <GlobalStyles />
      <Header isLoggedIn={isLoggedIn} showUserDropdown={showUserDropdown}
        setShowUserDropdown={setShowUserDropdown}
        onSearchClick={() => setIsSearchOpen(true)} onNavigate={handleNavigate} />
      <ExpandableSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
      
      {currentPage === 'main' && <MainPage isLoggedIn={isLoggedIn} onVideoClick={() => handleNavigate('video')} />}
      {currentPage === 'video' && <VideoDetailPage onNavigate={handleNavigate} />}
      {currentPage === 'mypage' && <MyPage onNavigate={handleNavigate} />}
      {currentPage === 'profile-edit' && <ProfileEditPage onNavigate={handleNavigate} />}
      {currentPage === 'all-comments' && <AllCommentsPage onNavigate={handleNavigate} />}
      
      <div style={{
        position: 'fixed', bottom: '24px', left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: '8px', backgroundColor: COLORS.overlay,
        padding: '10px 20px', borderRadius: '35px', zIndex: 100,
      }}>
        {[{ key: 'main', label: '메인' }, { key: 'video', label: '비디오' }, { key: 'mypage', label: '마이페이지' }].map((item) => (
          <button key={item.key} onClick={() => handleNavigate(item.key)} style={{
            padding: '10px 20px',
            backgroundColor: currentPage === item.key ? COLORS.primary : 'transparent',
            border: 'none', borderRadius: '25px',
            color: currentPage === item.key ? COLORS.textPrimary : COLORS.cardCream,
            cursor: 'pointer', fontWeight: '700', fontSize: '14px',
          }}>{item.label}</button>
        ))}
        <button onClick={() => setIsLoggedIn(!isLoggedIn)} style={{
          padding: '10px 16px', backgroundColor: 'transparent',
          border: `2px solid ${COLORS.primary}`, borderRadius: '25px',
          color: COLORS.primary, cursor: 'pointer', fontSize: '12px', fontWeight: '600',
        }}>{isLoggedIn ? '로그아웃' : '로그인'}</button>
      </div>
    </div>
  );
};

export default HistoryContentsApp;
