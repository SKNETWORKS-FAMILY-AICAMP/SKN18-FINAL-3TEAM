import React, { useState, useEffect, useRef } from 'react';

// 색상 상수
const COLORS = {
  primary: '#cffd1e',
  tag: '#7286ff',
  dark: '#1a1a1a',
  gray: '#666666',
  lightGray: '#e8e8e8',
  white: '#ffffff',
  overlay: 'rgba(80, 80, 80, 0.95)',
};

// ========== 아이콘 컴포넌트들 ==========
const LogoIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="18" cy="18" r="14" fill="#c8e0ff" />
    <path d="M28 12 C38 12, 42 20, 42 28 C42 36, 36 42, 28 42 C20 42, 18 38, 18 32" 
          fill={COLORS.primary} stroke="none"/>
    <circle cx="28" cy="42" r="5" fill="#333" />
  </svg>
);

const SearchIcon = ({ color = "#333" }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
);

const UserIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2">
    <circle cx="12" cy="8" r="4"/>
    <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>
  </svg>
);

const PlayIcon = () => (
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <polygon points="30,20 30,60 60,40" fill="#333"/>
  </svg>
);

const HeartIcon = ({ filled }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" 
       fill={filled ? "#e8a4b8" : "none"} 
       stroke="#e8a4b8" strokeWidth="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
);

const CloseIcon = ({ size = 24, color = "#333" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <path d="M18 6L6 18M6 6l12 12"/>
  </svg>
);

// ========== 확장형 검색 오버레이 컴포넌트 ==========
const ExpandableSearch = ({ isOpen, onClose }) => {
  const [searchValue, setSearchValue] = useState('');
  const [isAnimating, setIsAnimating] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const inputRef = useRef(null);

  const searchHistory = [
    '연평도에서 발생한 사건',
    '조선의 발명품',
    '임진왜란',
  ];
  
  const tags = ['# 발명품', '# 전쟁사', '# 세종', '# 정조', '# 양반', '# 과거제도', '# 한글', '# 실록'];

  // 추천 영상 데이터 (검색어 기반)
  const suggestedVideos = [
    { id: 1, title: '세종대왕의 한글 창제', tags: '#발명품 #세종', thumbnail: null },
    { id: 2, title: '임진왜란의 전개 과정', tags: '#전쟁사 #선조', thumbnail: null },
    { id: 3, title: '정조의 화성 건설', tags: '#건축 #정조', thumbnail: null },
    { id: 4, title: '조선시대 과거제도', tags: '#제도 #양반', thumbnail: null },
    { id: 5, title: '훈민정음 해례본', tags: '#발명품 #세종', thumbnail: null },
  ];

  useEffect(() => {
    if (isOpen) {
      setIsAnimating(true);
      document.body.style.overflow = 'hidden';
      setTimeout(() => {
        setContentVisible(true);
        inputRef.current?.focus();
      }, 300);
    } else {
      setContentVisible(false);
      setTimeout(() => {
        setIsAnimating(false);
        document.body.style.overflow = '';
      }, 300);
    }
  }, [isOpen]);

  const handleClose = () => {
    setContentVisible(false);
    setTimeout(() => {
      onClose();
    }, 200);
  };

  if (!isOpen && !isAnimating) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 9999,
      pointerEvents: isOpen ? 'auto' : 'none',
    }}>
      {/* 배경 오버레이 */}
      <div 
        onClick={handleClose}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(250, 250, 250, 0.98)',
          opacity: isOpen ? 1 : 0,
          transition: 'opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      />
      
      {/* 검색 컨테이너 */}
      <div style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transform: isOpen ? 'translateY(0)' : 'translateY(-20px)',
        opacity: isOpen ? 1 : 0,
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        
        {/* 상단 검색바 영역 */}
        <div style={{
          padding: '24px 60px',
          borderBottom: '1px solid #eee',
          backgroundColor: COLORS.white,
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
        }}>
          <span style={{
            fontSize: '16px',
            fontWeight: '600',
            color: COLORS.dark,
            minWidth: '50px',
          }}>검색</span>
          
          <SearchIcon color="#999" />
          
          <input
            ref={inputRef}
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="검색어를 입력하세요"
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              fontSize: '16px',
              backgroundColor: 'transparent',
              color: COLORS.dark,
            }}
          />
          
          <button 
            onClick={() => setSearchValue('')}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '14px',
              color: COLORS.gray,
              cursor: 'pointer',
              padding: '8px 16px',
            }}
          >
            초기화
          </button>
          
          <button 
            onClick={handleClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CloseIcon size={24} color="#333" />
          </button>
        </div>

        {/* 메인 콘텐츠 영역 */}
        <div style={{
          flex: 1,
          display: 'flex',
          padding: '40px 60px',
          gap: '60px',
          overflow: 'auto',
          opacity: contentVisible ? 1 : 0,
          transform: contentVisible ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1) 0.1s',
        }}>
          
          {/* 좌측: 검색 기록 & 태그 */}
          <div style={{
            flex: '0 0 40%',
            maxWidth: '500px',
          }}>
            {/* 검색 기록 */}
            <div style={{ marginBottom: '40px' }}>
              <h3 style={{
                fontSize: '15px',
                fontWeight: '700',
                color: COLORS.dark,
                marginBottom: '20px',
                letterSpacing: '0.5px',
              }}>검색 기록</h3>
              
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0',
              }}>
                {searchHistory.map((item, idx) => (
                  <div 
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '14px 0',
                      borderBottom: '1px solid #eee',
                      cursor: 'pointer',
                      opacity: contentVisible ? 1 : 0,
                      transform: contentVisible ? 'translateX(0)' : 'translateX(-20px)',
                      transition: `all 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${0.1 + idx * 0.05}s`,
                    }}
                    onClick={() => setSearchValue(item)}
                  >
                    <span style={{
                      fontSize: '14px',
                      color: COLORS.gray,
                    }}>{item}</span>
                    <button style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '4px',
                      opacity: 0.5,
                    }}>
                      <CloseIcon size={14} color="#999" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
            
            {/* 인기 태그 */}
            <div>
              <h3 style={{
                fontSize: '15px',
                fontWeight: '700',
                color: COLORS.dark,
                marginBottom: '20px',
                letterSpacing: '0.5px',
              }}>인기 태그</h3>
              
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '10px',
              }}>
                {tags.map((tag, idx) => (
                  <button 
                    key={idx}
                    onClick={() => setSearchValue(tag.replace('# ', ''))}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: 'transparent',
                      border: `1.5px solid ${COLORS.tag}`,
                      borderRadius: '25px',
                      color: COLORS.tag,
                      fontSize: '13px',
                      fontWeight: '500',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      opacity: contentVisible ? 1 : 0,
                      transform: contentVisible ? 'translateY(0)' : 'translateY(10px)',
                      transitionDelay: `${0.2 + idx * 0.03}s`,
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = COLORS.tag;
                      e.target.style.color = COLORS.white;
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = 'transparent';
                      e.target.style.color = COLORS.tag;
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 우측: 추천 영상 */}
          <div style={{ flex: 1 }}>
            <h3 style={{
              fontSize: '15px',
              fontWeight: '700',
              color: COLORS.dark,
              marginBottom: '20px',
              letterSpacing: '0.5px',
            }}>
              {searchValue ? `"${searchValue}" 관련 영상` : '추천 영상'}
            </h3>
            
            <div style={{
              display: 'flex',
              gap: '20px',
              overflowX: 'auto',
              paddingBottom: '20px',
            }}>
              {suggestedVideos.map((video, idx) => (
                <div 
                  key={video.id}
                  style={{
                    minWidth: '180px',
                    cursor: 'pointer',
                    opacity: contentVisible ? 1 : 0,
                    transform: contentVisible ? 'translateY(0)' : 'translateY(20px)',
                    transition: `all 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${0.15 + idx * 0.05}s`,
                  }}
                >
                  <div style={{
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
                    {/* 썸네일 플레이스홀더 */}
                    <div style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: `hsl(${idx * 30 + 200}, 20%, 90%)`,
                    }}>
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#bbb" strokeWidth="1.5">
                        <polygon points="5,3 19,12 5,21" fill="#ddd" stroke="none"/>
                      </svg>
                    </div>
                  </div>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: COLORS.dark,
                    marginBottom: '4px',
                    lineHeight: '1.4',
                  }}>{video.title}</div>
                  <div style={{
                    fontSize: '12px',
                    color: COLORS.gray,
                  }}>{video.tags}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 하단 로고 */}
        <div style={{
          position: 'absolute',
          bottom: '30px',
          left: '60px',
          opacity: contentVisible ? 0.6 : 0,
          transition: 'opacity 0.4s ease 0.3s',
        }}>
          <LogoIcon />
        </div>
      </div>
    </div>
  );
};

// ========== 헤더 컴포넌트 ==========
const Header = ({ isLoggedIn, showUserDropdown, setShowUserDropdown, onSearchClick }) => {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '20px 60px',
      backgroundColor: COLORS.white,
      borderBottom: '1px solid #eee',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <LogoIcon />
        <div style={{
          fontSize: '14px',
          fontWeight: '600',
          lineHeight: '1.3',
          color: COLORS.dark,
        }}>
          History &<br />Contents
        </div>
      </div>
      
      {/* 검색 버튼 (클릭 시 확장) */}
      <div 
        onClick={onSearchClick}
        style={{
          flex: 1,
          maxWidth: '600px',
          margin: '0 40px',
          position: 'relative',
          cursor: 'pointer',
        }}
      >
        <div style={{
          width: '100%',
          padding: '14px 50px 14px 20px',
          border: '2px solid #ddd',
          borderRadius: '30px',
          fontSize: '15px',
          backgroundColor: COLORS.white,
          color: '#999',
          transition: 'all 0.3s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = COLORS.primary;
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(207, 253, 30, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = '#ddd';
          e.currentTarget.style.boxShadow = 'none';
        }}
        >
          검색어를 입력하세요
        </div>
        <button style={{
          position: 'absolute',
          right: '6px',
          top: '50%',
          transform: 'translateY(-50%)',
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          backgroundColor: COLORS.primary,
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'transform 0.2s ease',
        }}>
          <SearchIcon />
        </button>
      </div>
      
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
      }}>
        <div style={{
          display: 'flex',
          border: '1px solid #ddd',
          borderRadius: '6px',
          overflow: 'hidden',
        }}>
          <button style={{
            padding: '8px 14px',
            border: 'none',
            backgroundColor: '#f5f5f5',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: '500',
          }}>한</button>
          <button style={{
            padding: '8px 14px',
            border: 'none',
            backgroundColor: 'transparent',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: '500',
          }}>EN</button>
        </div>
        
        <div style={{ position: 'relative' }}>
          <button 
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 16px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontSize: '15px',
              fontWeight: '500',
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: COLORS.primary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <UserIcon />
            </div>
            <span>{isLoggedIn ? '사용자' : '로그인'}</span>
          </button>
          
          {isLoggedIn && showUserDropdown && (
            <div style={{
              position: 'absolute',
              top: '50px',
              right: '0',
              backgroundColor: COLORS.overlay,
              borderRadius: '12px',
              padding: '12px 0',
              minWidth: '140px',
              zIndex: 1000,
            }}>
              <div style={{
                padding: '12px 20px',
                color: COLORS.primary,
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
              }}>나의 기록</div>
              <div style={{
                padding: '12px 20px',
                color: COLORS.primary,
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
              }}>→ 로그아웃</div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

// ========== 메인 페이지 ==========
const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const videos = [
    { id: 1, tags: '#전쟁사 #정조', title: '제목' },
    { id: 2, tags: '#발명품 #세종', title: '제목' },
    { id: 3, tags: '#전쟁사 #정조', title: '제목' },
    { id: 4, tags: '#전쟁사 #정조', title: '제목' },
    { id: 5, tags: '#전쟁사 #정조', title: '제목' },
    { id: 6, tags: '#전쟁사 #정조', title: '제목' },
  ];

  return (
    <main style={{ padding: '40px 60px' }}>
      <div style={{
        display: 'inline-block',
        padding: '10px 24px',
        backgroundColor: COLORS.primary,
        borderRadius: '25px',
        fontSize: '15px',
        fontWeight: '600',
        marginBottom: '30px',
        color: COLORS.dark,
      }}>
        {isLoggedIn ? '개인 추천 영상' : '인기있는 영상'}
      </div>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '30px',
      }}>
        {videos.map((video) => (
          <div 
            key={video.id} 
            style={{ cursor: 'pointer' }}
            onClick={() => onVideoClick(video)}
          >
            <div style={{
              width: '100%',
              aspectRatio: '16/10',
              backgroundColor: COLORS.lightGray,
              borderRadius: '12px',
              marginBottom: '12px',
              transition: 'transform 0.3s ease',
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            ></div>
            <div style={{
              fontSize: '13px',
              color: COLORS.gray,
              marginBottom: '6px',
            }}>{video.tags}</div>
            <div style={{
              fontSize: '17px',
              fontWeight: '600',
              color: COLORS.dark,
            }}>{video.title}</div>
          </div>
        ))}
      </div>
    </main>
  );
};

// ========== 비디오 상세 페이지 ==========
const VideoDetailPage = () => {
  const comments = [
    {
      id: 1,
      username: '사용자명',
      text: '해당 사건은 몇년도에 발생하였나요?',
      replies: [
        {
          id: 11,
          username: '안녕하세요 사용자님!',
          text: '해당 사건은 1425년(세종 7년)에 발생한 사건입니다.',
          isAI: true,
        }
      ]
    },
    {
      id: 2,
      username: '사용자명',
      text: '영상이 정말 마음에 들어요',
      replies: []
    }
  ];

  return (
    <div style={{
      display: 'flex',
      gap: '30px',
      padding: '30px 60px',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{
          width: '100%',
          aspectRatio: '16/9',
          backgroundColor: COLORS.lightGray,
          borderRadius: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <PlayIcon />
          <div style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            right: '20px',
            height: '6px',
            backgroundColor: 'rgba(0,0,0,0.2)',
            borderRadius: '3px',
          }}>
            <div style={{
              width: '25%',
              height: '100%',
              backgroundColor: COLORS.dark,
              borderRadius: '3px',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute',
                right: '-8px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '16px',
                height: '16px',
                backgroundColor: COLORS.white,
                borderRadius: '50%',
                boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
              }}></div>
            </div>
          </div>
        </div>
        
        <div style={{
          marginTop: '16px',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: '13px', color: COLORS.gray, marginBottom: '8px' }}>#전쟁사 #정조</div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: COLORS.dark }}>가나다라마바사</div>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '20px',
            fontSize: '14px',
            color: COLORS.gray,
          }}>
            <span>게시일 | 2025. 12. 01.</span>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: '#e8a4b8',
              cursor: 'pointer',
            }}>
              <span>좋아요.</span>
              <HeartIcon filled={false} />
            </div>
          </div>
        </div>
      </div>
      
      {/* 댓글 섹션 */}
      <div style={{
        width: '380px',
        backgroundColor: COLORS.white,
        borderRadius: '16px',
        border: '1px solid #eee',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: '600px',
      }}>
        <div style={{
          flex: 1,
          padding: '20px',
          overflowY: 'auto',
        }}>
          {comments.map((comment) => (
            <div key={comment.id} style={{ marginBottom: '20px' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginBottom: '8px',
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: COLORS.lightGray,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <UserIcon size={16} />
                </div>
                <span style={{ fontSize: '13px', fontWeight: '600', color: COLORS.dark }}>{comment.username}</span>
              </div>
              <div style={{
                fontSize: '14px',
                color: COLORS.dark,
                lineHeight: '1.5',
                marginLeft: '42px',
              }}>{comment.text}</div>
              
              {/* 대댓글 - 곡선 연결 */}
              {comment.replies.map((reply) => (
                <div key={reply.id} style={{
                  marginLeft: '20px',
                  marginTop: '12px',
                  position: 'relative',
                  paddingLeft: '22px',
                }}>
                  {/* 곡선 연결선 */}
                  <div style={{
                    position: 'absolute',
                    left: '0',
                    top: '-8px',
                    width: '16px',
                    height: '28px',
                    borderLeft: '2px solid #ddd',
                    borderBottom: '2px solid #ddd',
                    borderBottomLeftRadius: '12px',
                  }}></div>
                  
                  <div style={{
                    backgroundColor: '#f8f8f8',
                    borderRadius: '12px',
                    padding: '12px 16px',
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '6px',
                    }}>
                      <div style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        backgroundColor: reply.isAI ? COLORS.primary : COLORS.lightGray,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        {reply.isAI ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                            <circle cx="10" cy="10" r="6" fill="#c8e0ff"/>
                            <path d="M14 8c5 0 7 3 7 6s-2 8-6 8-5-3-5-6" fill={COLORS.primary}/>
                          </svg>
                        ) : <UserIcon size={12} />}
                      </div>
                      <span style={{ fontSize: '12px', fontWeight: '600', color: COLORS.dark }}>{reply.username}</span>
                    </div>
                    <div style={{ fontSize: '13px', color: COLORS.dark, lineHeight: '1.5' }}>{reply.text}</div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      marginTop: '8px',
                      fontSize: '12px',
                      color: '#999',
                    }}>
                      <span>좋아요</span>
                      <HeartIcon filled={false} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
        
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid #eee',
        }}>
          <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: COLORS.dark }}>댓글 작성하기</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: COLORS.lightGray,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <UserIcon size={16} />
            </div>
            <input
              type="text"
              placeholder=""
              style={{
                flex: 1,
                padding: '12px 16px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                fontSize: '14px',
                outline: 'none',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 마이페이지 ==========
const MyPage = () => {
  const watchHistory = [
    { id: 1, title: '제목' },
    { id: 2, title: '제목' },
    { id: 3, title: '제목' },
    { id: 4, title: '제목' },
  ];

  const chartColors = [COLORS.primary, '#7286ff', '#666', '#999', '#333'];

  return (
    <div style={{
      display: 'flex',
      gap: '40px',
      padding: '40px 60px',
    }}>
      <div style={{ width: '200px', textAlign: 'center' }}>
        <div style={{
          width: '160px',
          height: '160px',
          borderRadius: '50%',
          backgroundColor: COLORS.primary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
        }}>
          <UserIcon size={80} />
        </div>
        <button style={{
          padding: '10px 24px',
          border: '2px solid #333',
          borderRadius: '8px',
          backgroundColor: 'transparent',
          fontSize: '14px',
          fontWeight: '600',
          cursor: 'pointer',
        }}>수정하기</button>
      </div>
      
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div style={{
            display: 'inline-block',
            padding: '10px 20px',
            backgroundColor: COLORS.gray,
            borderRadius: '8px',
            color: COLORS.white,
            fontSize: '14px',
            fontWeight: '600',
          }}>내가 본 영상 기록</div>
        </div>
        
        <div style={{
          display: 'flex',
          gap: '20px',
          overflowX: 'auto',
          paddingBottom: '20px',
        }}>
          {watchHistory.map((item) => (
            <div key={item.id} style={{ minWidth: '140px' }}>
              <div style={{
                width: '140px',
                height: '100px',
                backgroundColor: COLORS.lightGray,
                borderRadius: '8px',
                marginBottom: '8px',
              }}></div>
              <div style={{ fontSize: '13px', color: COLORS.dark }}>{item.title}</div>
            </div>
          ))}
        </div>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '40px',
          marginTop: '40px',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <div style={{
                display: 'inline-block',
                padding: '10px 20px',
                backgroundColor: COLORS.gray,
                borderRadius: '8px',
                color: COLORS.white,
                fontSize: '14px',
                fontWeight: '600',
              }}>내가 남긴 댓글</div>
              <button style={{
                padding: '8px 16px',
                border: '1px solid #333',
                borderRadius: '6px',
                backgroundColor: 'transparent',
                fontSize: '13px',
                cursor: 'pointer',
              }}>전체보기</button>
            </div>
            <div style={{
              backgroundColor: COLORS.white,
              borderRadius: '12px',
              border: '1px solid #eee',
              padding: '20px',
            }}>
              <div style={{ padding: '16px 0', borderBottom: '1px solid #eee' }}>
                <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>영상 제목</div>
                <div style={{ marginLeft: '12px' }}>
                  <div style={{
                    fontSize: '13px',
                    color: COLORS.gray,
                    position: 'relative',
                    paddingLeft: '16px',
                    marginBottom: '6px',
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: '0',
                      top: '0',
                      width: '10px',
                      height: '100%',
                      borderLeft: '1.5px solid #ccc',
                      borderBottom: '1.5px solid #ccc',
                      borderBottomLeftRadius: '8px',
                    }}></div>
                    해당 사건은 몇년도에 발생하였나요?
                  </div>
                  <div style={{
                    fontSize: '13px',
                    color: COLORS.gray,
                    position: 'relative',
                    paddingLeft: '16px',
                    marginLeft: '16px',
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: '0',
                      top: '0',
                      width: '10px',
                      height: '100%',
                      borderLeft: '1.5px solid #ccc',
                      borderBottom: '1.5px solid #ccc',
                      borderBottomLeftRadius: '8px',
                    }}></div>
                    안녕하세요 사용자님!<br/>
                    해당 사건은 1425년(세종 7년)에 발생한 사건입니다.
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <div style={{
                display: 'inline-block',
                padding: '10px 20px',
                backgroundColor: COLORS.gray,
                borderRadius: '8px',
                color: COLORS.white,
                fontSize: '14px',
                fontWeight: '600',
              }}>기록 분석</div>
            </div>
            <div style={{
              backgroundColor: COLORS.white,
              borderRadius: '12px',
              border: '1px solid #eee',
              padding: '20px',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '30px',
                marginTop: '20px',
              }}>
                <svg width="160" height="160" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill={chartColors[0]} />
                  <path d="M50 50 L50 10 A40 40 0 0 1 90 50 Z" fill={chartColors[1]} />
                  <path d="M50 50 L90 50 A40 40 0 0 1 70 85 Z" fill={chartColors[2]} />
                  <path d="M50 50 L70 85 A40 40 0 0 1 30 85 Z" fill={chartColors[3]} />
                  <path d="M50 50 L30 85 A40 40 0 0 1 10 50 Z" fill={chartColors[4]} />
                </svg>
                
                <div style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}>
                  <div style={{ height: '16px', borderRadius: '4px', width: '100%', backgroundColor: chartColors[0] }}></div>
                  <div style={{ height: '16px', borderRadius: '4px', width: '75%', backgroundColor: chartColors[1] }}></div>
                  <div style={{ height: '16px', borderRadius: '4px', width: '50%', backgroundColor: chartColors[4] }}></div>
                  <div style={{ height: '16px', borderRadius: '4px', width: '30%', backgroundColor: chartColors[3] }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 메인 앱 ==========
const HistoryContentsApp = () => {
  const [currentPage, setCurrentPage] = useState('main');
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  
  const handleVideoClick = () => {
    setCurrentPage('video');
  };

  return (
    <div style={{
      fontFamily: "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
      backgroundColor: '#fafafa',
      minHeight: '100vh',
      color: COLORS.dark,
    }}>
      <Header 
        isLoggedIn={isLoggedIn}
        showUserDropdown={showUserDropdown}
        setShowUserDropdown={setShowUserDropdown}
        onSearchClick={() => setIsSearchOpen(true)}
      />
      
      {/* 확장형 검색 오버레이 */}
      <ExpandableSearch 
        isOpen={isSearchOpen} 
        onClose={() => setIsSearchOpen(false)} 
      />
      
      {currentPage === 'main' && (
        <MainPage 
          isLoggedIn={isLoggedIn} 
          onVideoClick={handleVideoClick}
        />
      )}
      
      {currentPage === 'video' && <VideoDetailPage />}
      
      {currentPage === 'mypage' && <MyPage />}
      
      {/* 테스트용 네비게이션 */}
      <div style={{
        position: 'fixed',
        bottom: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        gap: '10px',
        backgroundColor: '#333',
        padding: '10px 20px',
        borderRadius: '30px',
        zIndex: 100,
      }}>
        {['main', 'video', 'mypage'].map((page) => (
          <button 
            key={page}
            onClick={() => setCurrentPage(page)}
            style={{
              padding: '8px 16px',
              backgroundColor: currentPage === page ? COLORS.primary : 'transparent',
              border: 'none',
              borderRadius: '20px',
              color: currentPage === page ? '#333' : '#fff',
              cursor: 'pointer',
              fontWeight: '600',
            }}
          >
            {page === 'main' ? '메인' : page === 'video' ? '비디오' : '마이페이지'}
          </button>
        ))}
        <button 
          onClick={() => setIsLoggedIn(!isLoggedIn)}
          style={{
            padding: '8px 16px',
            backgroundColor: 'transparent',
            border: `1px solid ${COLORS.primary}`,
            borderRadius: '20px',
            color: COLORS.primary,
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          {isLoggedIn ? '로그아웃' : '로그인'}
        </button>
      </div>
    </div>
  );
};

export default HistoryContentsApp;
