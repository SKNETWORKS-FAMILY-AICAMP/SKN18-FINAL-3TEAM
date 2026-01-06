import { useState, useEffect, useCallback } from "react";
import { COLORS } from "./constants/theme";
import Header from "./components/layout/Header";
import ExpandableSearch from "./features/search/components/ExpandableSearch";
import MainPage from "./pages/MainPage";
import AboutPage from "./pages/AboutPage";
import VideoDetailPage from "./pages/VideoDetailPage";
import SearchResultPage from "./pages/SearchResultPage";
import MyPage from "./pages/MyPage";
import AllCommentsPage from "./pages/AllCommentsPage";
import ProfileEditPage from "./pages/ProfileEditPage";
import AdminPage from "./pages/AdminPage";
import VideoEditPage from "./pages/admin/VideoEditPage";
import Chatbot from "./pages/Chatbot";
import VideoCreatePage from "./pages/VideoCreatePage";
import ChatbotButton from "./components/common/ChatbotButton";
import {
  checkAuth,
  getGoogleLoginUrl,
  logout as apiLogout,
} from "./api/authApi";
import { BackgroundTaskProvider } from "./contexts/BackgroundTaskContext";

const App = () => {
  // URL에서 초기 페이지 상태 읽기
  const getInitialPage = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash) {
      const parts = hash.split("/");
      const [page, param, subPage, subParam] = parts;

      // 영상 편집 페이지 (#admin/video/edit/123)
      if (
        page === "admin" &&
        param === "video" &&
        subPage === "edit" &&
        subParam
      ) {
        return {
          page: "admin-video-edit",
          videoId: parseInt(subParam),
          searchQuery: "",
        };
      }

      // 영상 상세 페이지
      if (page === "video" && param) {
        return {
          page: "video",
          videoId: parseInt(param),
          searchQuery: "",
        };
      }

      // 검색 결과 페이지
      if (page === "search" && param) {
        return {
          page: "search",
          videoId: null,
          searchQuery: decodeURIComponent(param),
        };
      }

      // 챗봇 세션 페이지 (#question/session/123)
      if (page === "question" && param === "session" && subPage) {
        return {
          page: "question",
          videoId: null,
          searchQuery: "",
          sessionId: parseInt(subPage),
        };
      }

      return {
        page: page || "main",
        videoId: null,
        searchQuery: "",
      };
    }
    return { page: "main", videoId: null, searchQuery: "" };
  };

  const initial = getInitialPage();
  const [currentPage, setCurrentPage] = useState(initial.page);
  const [selectedVideoId, setSelectedVideoId] = useState(initial.videoId);
  const [searchQuery, setSearchQuery] = useState(initial.searchQuery || "");
  const [initialSessionId, setInitialSessionId] = useState(
    initial.sessionId || null
  );
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [newChatTrigger, setNewChatTrigger] = useState(0);

  // URL 변경 감지 (뒤로가기/앞으로가기 지원)
  useEffect(() => {
    const handleHashChange = () => {
      const initial = getInitialPage();
      setCurrentPage(initial.page);
      setSelectedVideoId(initial.videoId);
      setSearchQuery(initial.searchQuery || "");
      setInitialSessionId(initial.sessionId || null);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // 인증 상태 확인
  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const response = await checkAuth();
        if (response.isAuthenticated) {
          setIsLoggedIn(true);
          setUser(response.user);
        } else {
          setIsLoggedIn(false);
          setUser(null);
        }
      } catch (error) {
        // 네트워크 에러인 경우 (백엔드 서버가 실행되지 않은 경우)
        if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
          // 개발 환경에서만 경고 표시
          if (import.meta.env.DEV) {
            console.warn(
              "⚠️ 백엔드 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요."
            );
          }
          // 네트워크 에러는 조용히 처리 (비로그인 상태로 설정)
          setIsLoggedIn(false);
          setUser(null);
        } else if (
          error.response?.status === 401 ||
          error.response?.status === 403
        ) {
          // 401/403 에러는 토큰 만료 또는 인증 실패
          // axios 인터셉터에서 이미 처리했지만, 여기서도 상태 초기화
          console.warn("⚠️ 인증 실패. 로그아웃 처리...");
          localStorage.clear();
          setIsLoggedIn(false);
          setUser(null);
          // 강제 새로고침 (프론트엔드 URL로 리다이렉트)
          setTimeout(() => {
            const frontendUrl =
              window.location.port === "8000" ||
              window.location.hostname.includes("8000")
                ? "http://localhost:3000/"
                : `${window.location.origin}/`;
            window.location.href = frontendUrl;
          }, 100);
        } else {
          // 기타 에러는 콘솔에 표시
          console.error("인증 확인 실패:", error);
          setIsLoggedIn(false);
          setUser(null);
        }
      } finally {
        setIsLoading(false);
      }
    };

    verifyAuth();

    // URL에서 토큰 확인 (Google OAuth 콜백 처리)
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get("access");
    const refreshToken = urlParams.get("refresh");

    if (accessToken && refreshToken) {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      // URL에서 토큰 제거
      window.history.replaceState({}, document.title, window.location.pathname);
      // 토큰 저장 후 인증 확인
      verifyAuth();
    }
  }, []);

  // URL 업데이트 헬퍼 함수
  const updateURL = (page, videoId = null) => {
    if (videoId) {
      window.location.hash = `${page}/${videoId}`;
    } else {
      window.location.hash = page;
    }
  };

  const handleVideoClick = (video) => {
    if (!video || !video.id) {
      return;
    }
    setSelectedVideoId(video.id);
    setCurrentPage("video");
    updateURL("video", video.id);
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  const handleLogoClick = () => {
    setCurrentPage("main");
    updateURL("main");
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  const handleMyPageClick = () => {
    setCurrentPage("mypage");
    updateURL("mypage");
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  const handleAdminClick = () => {
    setCurrentPage("admin");
    updateURL("admin");
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  const handleLogin = () => {
    // Google 로그인 페이지로 리다이렉트
    window.location.href = getGoogleLoginUrl();
  };

  const handleLogout = async () => {
    try {
      await apiLogout();
      setIsLoggedIn(false);
      setUser(null);
      setShowUserDropdown(false);

      // 인증이 필요한 페이지에서 로그아웃 시 메인으로 이동
      const authRequiredPages = [
        "mypage",
        "profile-edit",
        "all-comments",
        "admin",
        "question",
        "video-create",
      ];
      if (authRequiredPages.includes(currentPage)) {
        setCurrentPage("main");
        updateURL("main");
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      }
    } catch (error) {
      console.error("로그아웃 실패:", error);
      // 에러가 발생해도 로컬 상태는 초기화
      setIsLoggedIn(false);
      setUser(null);
      setShowUserDropdown(false);

      // 에러가 발생해도 인증 필요 페이지면 메인으로 이동
      const authRequiredPages = [
        "mypage",
        "profile-edit",
        "all-comments",
        "admin",
        "question",
        "video-create",
      ];
      if (authRequiredPages.includes(currentPage)) {
        setCurrentPage("main");
        updateURL("main");
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      }
    }
  };

  // 프로필 업데이트 콜백 함수
  const handleUserUpdate = useCallback((updatedUser) => {
    setUser(updatedUser);
  }, []);

  const handleNavigate = (page, videoId = null, options = {}) => {
    if (!isLoggedIn && (page === "question" || page === "video-create")) {
      return;
    }
    if (options.newChat) {
      setNewChatTrigger((prev) => prev + 1);
    }
    setCurrentPage(page);
    updateURL(page, videoId);
    // 페이지 전환 시 스크롤을 맨 위로 이동
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  // 검색 결과 페이지로 이동 (로그인 여부와 관계없이 모든 사용자에게 허용)
  const handleSearch = (query) => {
    setSearchQuery(query);
    setCurrentPage("search");
    window.location.hash = `search/${encodeURIComponent(query)}`;
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  return (
    <BackgroundTaskProvider>
      <div
        style={{
          fontFamily: "'Noto Serif KR', serif",
          backgroundColor: COLORS.background,
          minHeight: "100vh",
          width: "100%",
          margin: 0,
          padding: 0,
          color: COLORS.white,
          overflowX: "hidden",
        }}
      >
        <Header
          isLoggedIn={isLoggedIn}
          user={user}
          showUserDropdown={showUserDropdown}
          setShowUserDropdown={setShowUserDropdown}
          onSearchClick={() => setIsSearchOpen(true)}
          onLogoClick={handleLogoClick}
          onMyPageClick={handleMyPageClick}
          onLogin={handleLogin}
          onLogout={handleLogout}
          onAdminClick={handleAdminClick}
          currentPage={currentPage}
          onNavigate={handleNavigate}
        />

        <ExpandableSearch
          isOpen={isSearchOpen}
          isLoggedIn={isLoggedIn}
          onClose={() => setIsSearchOpen(false)}
          onSearch={handleSearch}
          onVideoClick={handleVideoClick}
        />

        <div style={{ paddingTop: "76px" }}>
          {currentPage === "main" && (
            <MainPage isLoggedIn={isLoggedIn} onVideoClick={handleVideoClick} />
          )}

          {currentPage === "about" && <AboutPage onNavigate={handleNavigate} />}

          {currentPage === "video" && (
            <VideoDetailPage
              videoId={selectedVideoId}
              isLoggedIn={isLoggedIn}
              user={user}
            />
          )}

          {currentPage === "search" && (
            <SearchResultPage
              query={searchQuery}
              onVideoClick={handleVideoClick}
              isLoggedIn={isLoggedIn}
            />
          )}

          {currentPage === "mypage" && (
            <MyPage onNavigate={handleNavigate} user={user} />
          )}

          {currentPage === "all-comments" && (
            <AllCommentsPage onNavigate={handleNavigate} />
          )}

          {currentPage === "profile-edit" && (
            <ProfileEditPage
              onNavigate={handleNavigate}
              user={user}
              onUserUpdate={handleUserUpdate}
            />
          )}

          {currentPage === "admin" && (
            <AdminPage onNavigate={handleNavigate} user={user} />
          )}

          {currentPage === "admin-video-edit" && (
            <VideoEditPage videoId={selectedVideoId} />
          )}

          {currentPage === "question" && (
            <div style={{ overflow: "hidden", height: "calc(100vh - 76px)" }}>
              <Chatbot
                onNavigate={handleNavigate}
                user={user}
                newChatTrigger={newChatTrigger}
                initialSessionId={initialSessionId}
              />
            </div>
          )}

          {currentPage === "video-create" && (
            <VideoCreatePage onNavigate={handleNavigate} user={user} />
          )}
        </div>

        {/* 챗봇 버튼 (로그인 시에만 표시) */}
        {isLoggedIn && <ChatbotButton onNavigate={handleNavigate} />}
      </div>
    </BackgroundTaskProvider>
  );
};

export default App;
