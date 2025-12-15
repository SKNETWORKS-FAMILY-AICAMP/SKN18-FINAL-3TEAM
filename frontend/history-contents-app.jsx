import React, { useState } from 'react';

// 색상 상수
const COLORS = {
  primary: '#cffd1e',      // 포인트 색상 (연두)
  tag: '#7286ff',          // 태그 색상 (보라)
  dark: '#1a1a1a',
  gray: '#666666',
  lightGray: '#e8e8e8',
  white: '#ffffff',
  overlay: 'rgba(80, 80, 80, 0.95)',
};

// 커스텀 스타일
const styles = {
  // 전역 스타일
  container: {
    fontFamily: "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
    backgroundColor: '#fafafa',
    minHeight: '100vh',
    color: COLORS.dark,
  },
  
  // 헤더 스타일
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 60px',
    backgroundColor: COLORS.white,
    borderBottom: '1px solid #eee',
  },
  
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  
  logoIcon: {
    width: '48px',
    height: '48px',
    position: 'relative',
  },
  
  logoText: {
    fontSize: '14px',
    fontWeight: '600',
    lineHeight: '1.3',
    color: COLORS.dark,
  },
  
  // 검색창 스타일
  searchContainer: {
    position: 'relative',
    flex: 1,
    maxWidth: '600px',
    margin: '0 40px',
  },
  
  searchInput: {
    width: '100%',
    padding: '14px 50px 14px 20px',
    border: '2px solid #ddd',
    borderRadius: '30px',
    fontSize: '15px',
    outline: 'none',
    transition: 'border-color 0.2s ease',
    backgroundColor: COLORS.white,
  },
  
  searchButton: {
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
  },
  
  // 검색 드롭다운 스타일
  searchDropdown: {
    position: 'absolute',
    top: '60px',
    left: '0',
    right: '0',
    backgroundColor: COLORS.overlay,
    borderRadius: '16px',
    padding: '24px',
    zIndex: 1000,
    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
  },
  
  dropdownTitle: {
    color: COLORS.white,
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '16px',
  },
  
  searchHistoryItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 0',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.8)',
    fontSize: '14px',
  },
  
  tagsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
    marginTop: '20px',
  },
  
  tag: {
    padding: '8px 16px',
    backgroundColor: 'transparent',
    border: `1.5px solid ${COLORS.tag}`,
    borderRadius: '20px',
    color: COLORS.tag,
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  
  closeButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: COLORS.primary,
    fontSize: '13px',
    cursor: 'pointer',
    marginTop: '20px',
    justifyContent: 'flex-end',
  },
  
  // 헤더 우측 영역
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  
  langToggle: {
    display: 'flex',
    border: '1px solid #ddd',
    borderRadius: '6px',
    overflow: 'hidden',
  },
  
  langBtn: {
    padding: '8px 14px',
    border: 'none',
    backgroundColor: 'transparent',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  
  langBtnActive: {
    backgroundColor: '#f5f5f5',
  },
  
  userButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 16px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: '500',
  },
  
  userIcon: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    backgroundColor: COLORS.primary,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  
  // 사용자 드롭다운
  userDropdown: {
    position: 'absolute',
    top: '50px',
    right: '0',
    backgroundColor: COLORS.overlay,
    borderRadius: '12px',
    padding: '12px 0',
    minWidth: '140px',
    zIndex: 1000,
  },
  
  userDropdownItem: {
    padding: '12px 20px',
    color: COLORS.primary,
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  
  // 메인 콘텐츠
  main: {
    padding: '40px 60px',
  },
  
  sectionLabel: {
    display: 'inline-block',
    padding: '10px 24px',
    backgroundColor: COLORS.primary,
    borderRadius: '25px',
    fontSize: '15px',
    fontWeight: '600',
    marginBottom: '30px',
    color: COLORS.dark,
  },
  
  // 비디오 그리드
  videoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '30px',
  },
  
  videoCard: {
    cursor: 'pointer',
    transition: 'transform 0.2s ease',
  },
  
  videoThumbnail: {
    width: '100%',
    aspectRatio: '16/10',
    backgroundColor: COLORS.lightGray,
    borderRadius: '12px',
    marginBottom: '12px',
  },
  
  videoTags: {
    fontSize: '13px',
    color: COLORS.gray,
    marginBottom: '6px',
  },
  
  videoTitle: {
    fontSize: '17px',
    fontWeight: '600',
    color: COLORS.dark,
  },
  
  // 비디오 상세 페이지
  videoDetailContainer: {
    display: 'flex',
    gap: '30px',
    padding: '30px 60px',
  },
  
  videoPlayerSection: {
    flex: 1,
  },
  
  videoPlayer: {
    width: '100%',
    aspectRatio: '16/9',
    backgroundColor: COLORS.lightGray,
    borderRadius: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  
  playButton: {
    width: '80px',
    height: '80px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
  },
  
  progressBar: {
    position: 'absolute',
    bottom: '20px',
    left: '20px',
    right: '20px',
    height: '6px',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: '3px',
  },
  
  progressFill: {
    width: '25%',
    height: '100%',
    backgroundColor: COLORS.dark,
    borderRadius: '3px',
    position: 'relative',
  },
  
  progressHandle: {
    position: 'absolute',
    right: '-8px',
    top: '50%',
    transform: 'translateY(-50%)',
    width: '16px',
    height: '16px',
    backgroundColor: COLORS.white,
    borderRadius: '50%',
    boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
  },
  
  videoInfo: {
    marginTop: '16px',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  
  videoMetaTags: {
    fontSize: '13px',
    color: COLORS.gray,
    marginBottom: '8px',
  },
  
  videoMetaTitle: {
    fontSize: '24px',
    fontWeight: '700',
    color: COLORS.dark,
  },
  
  videoMetaRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    fontSize: '14px',
    color: COLORS.gray,
  },
  
  likeButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: '#e8a4b8',
    cursor: 'pointer',
  },
  
  // 댓글 섹션
  commentSection: {
    width: '380px',
    backgroundColor: COLORS.white,
    borderRadius: '16px',
    border: '1px solid #eee',
    display: 'flex',
    flexDirection: 'column',
    maxHeight: '600px',
  },
  
  commentList: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
  },
  
  commentItem: {
    marginBottom: '20px',
  },
  
  commentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '8px',
  },
  
  commentAvatar: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    backgroundColor: COLORS.lightGray,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  
  commentUsername: {
    fontSize: '13px',
    fontWeight: '600',
    color: COLORS.dark,
  },
  
  commentText: {
    fontSize: '14px',
    color: COLORS.dark,
    lineHeight: '1.5',
    marginLeft: '42px',
  },
  
  // 대댓글 스타일 (곡선 연결선)
  replyContainer: {
    marginLeft: '20px',
    marginTop: '12px',
    position: 'relative',
    paddingLeft: '22px',
  },
  
  replyCurve: {
    position: 'absolute',
    left: '0',
    top: '-8px',
    width: '16px',
    height: '28px',
    borderLeft: '2px solid #ddd',
    borderBottom: '2px solid #ddd',
    borderBottomLeftRadius: '12px',
  },
  
  replyContent: {
    backgroundColor: '#f8f8f8',
    borderRadius: '12px',
    padding: '12px 16px',
  },
  
  replyHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  
  replyAvatar: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: COLORS.primary,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  
  replyUsername: {
    fontSize: '12px',
    fontWeight: '600',
    color: COLORS.dark,
  },
  
  replyText: {
    fontSize: '13px',
    color: COLORS.dark,
    lineHeight: '1.5',
  },
  
  replyLike: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    marginTop: '8px',
    fontSize: '12px',
    color: '#999',
  },
  
  // 댓글 입력
  commentInputSection: {
    padding: '16px 20px',
    borderTop: '1px solid #eee',
  },
  
  commentInputLabel: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '12px',
    color: COLORS.dark,
  },
  
  commentInputWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  
  commentInput: {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
  },
  
  // 마이페이지
  myPageContainer: {
    display: 'flex',
    gap: '40px',
    padding: '40px 60px',
  },
  
  profileSection: {
    width: '200px',
    textAlign: 'center',
  },
  
  profileAvatar: {
    width: '160px',
    height: '160px',
    borderRadius: '50%',
    backgroundColor: COLORS.primary,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 20px',
  },
  
  editButton: {
    padding: '10px 24px',
    border: '2px solid #333',
    borderRadius: '8px',
    backgroundColor: 'transparent',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  
  contentSection: {
    flex: 1,
  },
  
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  
  sectionTitle: {
    display: 'inline-block',
    padding: '10px 20px',
    backgroundColor: COLORS.gray,
    borderRadius: '8px',
    color: COLORS.white,
    fontSize: '14px',
    fontWeight: '600',
  },
  
  viewAllButton: {
    padding: '8px 16px',
    border: '1px solid #333',
    borderRadius: '6px',
    backgroundColor: 'transparent',
    fontSize: '13px',
    cursor: 'pointer',
  },
  
  historyGrid: {
    display: 'flex',
    gap: '20px',
    overflowX: 'auto',
    paddingBottom: '20px',
  },
  
  historyCard: {
    minWidth: '140px',
  },
  
  historyThumbnail: {
    width: '140px',
    height: '100px',
    backgroundColor: COLORS.lightGray,
    borderRadius: '8px',
    marginBottom: '8px',
  },
  
  historyTitle: {
    fontSize: '13px',
    color: COLORS.dark,
  },
  
  twoColumnLayout: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '40px',
    marginTop: '40px',
  },
  
  myCommentsSection: {
    backgroundColor: COLORS.white,
    borderRadius: '12px',
    border: '1px solid #eee',
    padding: '20px',
  },
  
  myCommentItem: {
    padding: '16px 0',
    borderBottom: '1px solid #eee',
  },
  
  myCommentVideoTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '8px',
  },
  
  myCommentThread: {
    marginLeft: '12px',
  },
  
  myCommentText: {
    fontSize: '13px',
    color: COLORS.gray,
    position: 'relative',
    paddingLeft: '16px',
    marginBottom: '6px',
  },
  
  myCommentCurve: {
    position: 'absolute',
    left: '0',
    top: '0',
    width: '10px',
    height: '100%',
    borderLeft: '1.5px solid #ccc',
    borderBottom: '1.5px solid #ccc',
    borderBottomLeftRadius: '8px',
  },
  
  analyticsSection: {
    backgroundColor: COLORS.white,
    borderRadius: '12px',
    border: '1px solid #eee',
    padding: '20px',
  },
  
  chartContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '30px',
    marginTop: '20px',
  },
  
  pieChart: {
    width: '160px',
    height: '160px',
  },
  
  barChart: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  
  barItem: {
    height: '16px',
    borderRadius: '4px',
  },
};

// 로고 아이콘 컴포넌트
const LogoIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="18" cy="18" r="14" fill="#c8e0ff" />
    <path d="M28 12 C38 12, 42 20, 42 28 C42 36, 36 42, 28 42 C20 42, 18 38, 18 32" 
          fill={COLORS.primary} stroke="none"/>
    <circle cx="28" cy="42" r="5" fill="#333" />
  </svg>
);

// 검색 아이콘
const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2.5">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
);

// 사용자 아이콘
const UserIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2">
    <circle cx="12" cy="8" r="4"/>
    <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>
  </svg>
);

// 재생 버튼 아이콘
const PlayIcon = () => (
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <polygon points="30,20 30,60 60,40" fill="#333"/>
  </svg>
);

// 하트 아이콘
const HeartIcon = ({ filled }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" 
       fill={filled ? "#e8a4b8" : "none"} 
       stroke="#e8a4b8" strokeWidth="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
);

// X 아이콘
const CloseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 6L6 18M6 6l12 12"/>
  </svg>
);

// ========== 헤더 컴포넌트 ==========
const Header = ({ isLoggedIn, onLoginClick, showUserDropdown, setShowUserDropdown }) => {
  const [searchFocused, setSearchFocused] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  
  const searchHistory = [
    '연평도에서 발생한 사건',
    '조선의 발명품',
  ];
  
  const tags = ['# 발명품', '# 전쟁사', '# 발명품', '# 전쟁사', '# 발명품', '# 전쟁사', 
                '# 발명품', '# 전쟁사', '# 세종', '# 양반'];

  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <LogoIcon />
        <div style={styles.logoText}>
          History &<br />Contents
        </div>
      </div>
      
      <div style={styles.searchContainer}>
        <input
          type="text"
          style={{
            ...styles.searchInput,
            borderColor: searchFocused ? COLORS.primary : '#ddd',
          }}
          placeholder=""
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
        />
        <button style={styles.searchButton}>
          <SearchIcon />
        </button>
        
        {searchFocused && (
          <div style={styles.searchDropdown}>
            <div style={styles.dropdownTitle}>검색 기록</div>
            {searchHistory.map((item, idx) => (
              <div key={idx} style={styles.searchHistoryItem}>
                <span>{item}</span>
                <CloseIcon />
              </div>
            ))}
            
            <div style={styles.tagsContainer}>
              {tags.map((tag, idx) => (
                <button key={idx} style={styles.tag}>
                  {tag}
                </button>
              ))}
            </div>
            
            <div style={styles.closeButton}>
              <CloseIcon />
              <span>close</span>
            </div>
          </div>
        )}
      </div>
      
      <div style={styles.headerRight}>
        <div style={styles.langToggle}>
          <button style={{...styles.langBtn, ...styles.langBtnActive}}>한</button>
          <button style={styles.langBtn}>EN</button>
        </div>
        
        <div style={{ position: 'relative' }}>
          <button 
            style={styles.userButton}
            onClick={() => setShowUserDropdown(!showUserDropdown)}
          >
            <div style={styles.userIcon}>
              <UserIcon />
            </div>
            <span>{isLoggedIn ? '사용자' : '로그인'}</span>
          </button>
          
          {isLoggedIn && showUserDropdown && (
            <div style={styles.userDropdown}>
              <div style={styles.userDropdownItem}>나의 기록</div>
              <div style={styles.userDropdownItem}>→ 로그아웃</div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

// ========== 메인 페이지 (비디오 그리드) ==========
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
    <main style={styles.main}>
      <div style={styles.sectionLabel}>
        {isLoggedIn ? '개인 추천 영상' : '인기있는 영상'}
      </div>
      
      <div style={styles.videoGrid}>
        {videos.map((video) => (
          <div 
            key={video.id} 
            style={styles.videoCard}
            onClick={() => onVideoClick(video)}
          >
            <div style={styles.videoThumbnail}></div>
            <div style={styles.videoTags}>{video.tags}</div>
            <div style={styles.videoTitle}>{video.title}</div>
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
    <div style={styles.videoDetailContainer}>
      <div style={styles.videoPlayerSection}>
        <div style={styles.videoPlayer}>
          <button style={styles.playButton}>
            <PlayIcon />
          </button>
          <div style={styles.progressBar}>
            <div style={styles.progressFill}>
              <div style={styles.progressHandle}></div>
            </div>
          </div>
        </div>
        
        <div style={styles.videoInfo}>
          <div>
            <div style={styles.videoMetaTags}>#전쟁사 #정조</div>
            <div style={styles.videoMetaTitle}>가나다라마바사</div>
          </div>
          <div style={styles.videoMetaRight}>
            <span>게시일 | 2025. 12. 01.</span>
            <div style={styles.likeButton}>
              <span>좋아요.</span>
              <HeartIcon filled={false} />
            </div>
          </div>
        </div>
      </div>
      
      <div style={styles.commentSection}>
        <div style={styles.commentList}>
          {comments.map((comment) => (
            <div key={comment.id} style={styles.commentItem}>
              <div style={styles.commentHeader}>
                <div style={styles.commentAvatar}>
                  <UserIcon size={16} />
                </div>
                <span style={styles.commentUsername}>{comment.username}</span>
              </div>
              <div style={styles.commentText}>{comment.text}</div>
              
              {comment.replies.map((reply) => (
                <div key={reply.id} style={styles.replyContainer}>
                  <div style={styles.replyCurve}></div>
                  <div style={styles.replyContent}>
                    <div style={styles.replyHeader}>
                      <div style={{
                        ...styles.replyAvatar,
                        backgroundColor: reply.isAI ? COLORS.primary : COLORS.lightGray,
                      }}>
                        {reply.isAI ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                            <circle cx="10" cy="10" r="6" fill="#c8e0ff"/>
                            <path d="M14 8c5 0 7 3 7 6s-2 8-6 8-5-3-5-6" fill={COLORS.primary}/>
                          </svg>
                        ) : <UserIcon size={12} />}
                      </div>
                      <span style={styles.replyUsername}>{reply.username}</span>
                    </div>
                    <div style={styles.replyText}>{reply.text}</div>
                    <div style={styles.replyLike}>
                      <span>좋아요</span>
                      <HeartIcon filled={false} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
        
        <div style={styles.commentInputSection}>
          <div style={styles.commentInputLabel}>댓글 작성하기</div>
          <div style={styles.commentInputWrapper}>
            <div style={styles.commentAvatar}>
              <UserIcon size={16} />
            </div>
            <input
              type="text"
              style={styles.commentInput}
              placeholder=""
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
    <div style={styles.myPageContainer}>
      <div style={styles.profileSection}>
        <div style={styles.profileAvatar}>
          <UserIcon size={80} />
        </div>
        <button style={styles.editButton}>수정하기</button>
      </div>
      
      <div style={styles.contentSection}>
        <div style={styles.sectionHeader}>
          <div style={styles.sectionTitle}>내가 본 영상 기록</div>
        </div>
        
        <div style={styles.historyGrid}>
          {watchHistory.map((item) => (
            <div key={item.id} style={styles.historyCard}>
              <div style={styles.historyThumbnail}></div>
              <div style={styles.historyTitle}>{item.title}</div>
            </div>
          ))}
        </div>
        
        <div style={styles.twoColumnLayout}>
          <div>
            <div style={styles.sectionHeader}>
              <div style={styles.sectionTitle}>내가 남긴 댓글</div>
              <button style={styles.viewAllButton}>전체보기</button>
            </div>
            <div style={styles.myCommentsSection}>
              <div style={styles.myCommentItem}>
                <div style={styles.myCommentVideoTitle}>영상 제목</div>
                <div style={styles.myCommentThread}>
                  <div style={styles.myCommentText}>
                    <div style={styles.myCommentCurve}></div>
                    해당 사건은 몇년도에 발생하였나요?
                  </div>
                  <div style={{...styles.myCommentText, marginLeft: '16px'}}>
                    <div style={styles.myCommentCurve}></div>
                    안녕하세요 사용자님!<br/>
                    해당 사건은 1425년(세종 7년)에 발생한 사건입니다.
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div>
            <div style={styles.sectionHeader}>
              <div style={styles.sectionTitle}>기록 분석</div>
            </div>
            <div style={styles.analyticsSection}>
              <div style={styles.chartContainer}>
                <svg style={styles.pieChart} viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill={chartColors[0]} />
                  <path d="M50 50 L50 10 A40 40 0 0 1 90 50 Z" fill={chartColors[1]} />
                  <path d="M50 50 L90 50 A40 40 0 0 1 70 85 Z" fill={chartColors[2]} />
                  <path d="M50 50 L70 85 A40 40 0 0 1 30 85 Z" fill={chartColors[3]} />
                  <path d="M50 50 L30 85 A40 40 0 0 1 10 50 Z" fill={chartColors[4]} />
                </svg>
                
                <div style={styles.barChart}>
                  <div style={{...styles.barItem, width: '100%', backgroundColor: chartColors[0]}}></div>
                  <div style={{...styles.barItem, width: '75%', backgroundColor: chartColors[1]}}></div>
                  <div style={{...styles.barItem, width: '50%', backgroundColor: chartColors[4]}}></div>
                  <div style={{...styles.barItem, width: '30%', backgroundColor: chartColors[3]}}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== 메인 앱 컴포넌트 ==========
const HistoryContentsApp = () => {
  const [currentPage, setCurrentPage] = useState('main'); // 'main', 'video', 'mypage'
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  
  const handleVideoClick = (video) => {
    setCurrentPage('video');
  };

  return (
    <div style={styles.container}>
      <Header 
        isLoggedIn={isLoggedIn}
        showUserDropdown={showUserDropdown}
        setShowUserDropdown={setShowUserDropdown}
      />
      
      {currentPage === 'main' && (
        <MainPage 
          isLoggedIn={isLoggedIn} 
          onVideoClick={handleVideoClick}
        />
      )}
      
      {currentPage === 'video' && <VideoDetailPage />}
      
      {currentPage === 'mypage' && <MyPage />}
      
      {/* 페이지 네비게이션 (테스트용) */}
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
      }}>
        <button 
          onClick={() => setCurrentPage('main')}
          style={{
            padding: '8px 16px',
            backgroundColor: currentPage === 'main' ? COLORS.primary : 'transparent',
            border: 'none',
            borderRadius: '20px',
            color: currentPage === 'main' ? '#333' : '#fff',
            cursor: 'pointer',
            fontWeight: '600',
          }}
        >
          메인
        </button>
        <button 
          onClick={() => setCurrentPage('video')}
          style={{
            padding: '8px 16px',
            backgroundColor: currentPage === 'video' ? COLORS.primary : 'transparent',
            border: 'none',
            borderRadius: '20px',
            color: currentPage === 'video' ? '#333' : '#fff',
            cursor: 'pointer',
            fontWeight: '600',
          }}
        >
          비디오
        </button>
        <button 
          onClick={() => setCurrentPage('mypage')}
          style={{
            padding: '8px 16px',
            backgroundColor: currentPage === 'mypage' ? COLORS.primary : 'transparent',
            border: 'none',
            borderRadius: '20px',
            color: currentPage === 'mypage' ? '#333' : '#fff',
            cursor: 'pointer',
            fontWeight: '600',
          }}
        >
          마이페이지
        </button>
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
