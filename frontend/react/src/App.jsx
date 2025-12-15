import { useState } from "react";
import { COLORS } from "./constants/theme";
import Header from "./components/layout/Header";
import ExpandableSearch from "./features/search/components/ExpandableSearch";
import MainPage from "./pages/MainPage";
import VideoDetailPage from "./pages/VideoDetailPage";
import MyPage from "./pages/MyPage";
import AllCommentsPage from "./pages/AllCommentsPage";
import ProfileEditPage from "./pages/ProfileEditPage";

const App = () => {
  const [currentPage, setCurrentPage] = useState("main");
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const handleVideoClick = () => {
    setCurrentPage("video");
  };

  const handleLogoClick = () => {
    setCurrentPage("main");
  };

  const handleMyPageClick = () => {
    setCurrentPage("mypage");
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setShowUserDropdown(false);
  };

  const handleNavigate = (page) => {
    setCurrentPage(page);
  };

  return (
    <>
      <style>{`
        ::selection {
          background-color: #c2e0f6;
          color: #effd9a;
        }
        ::-moz-selection {
          background-color: #c2e0f6;
          color: #effd9a;
        }
      `}</style>

      <div
        style={{
          fontFamily:
            "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
          backgroundColor: COLORS.background,
          minHeight: "100vh",
          color: COLORS.dark,
        }}
      >
        <Header
          isLoggedIn={isLoggedIn}
          showUserDropdown={showUserDropdown}
          setShowUserDropdown={setShowUserDropdown}
          onSearchClick={() => setIsSearchOpen(true)}
          onLogoClick={handleLogoClick}
          onMyPageClick={handleMyPageClick}
          onLogout={handleLogout}
        />

        <ExpandableSearch
          isOpen={isSearchOpen}
          onClose={() => setIsSearchOpen(false)}
        />

        <div style={{ paddingTop: "76px" }}>
          {currentPage === "main" && (
            <MainPage isLoggedIn={isLoggedIn} onVideoClick={handleVideoClick} />
          )}

          {currentPage === "video" && <VideoDetailPage />}

          {currentPage === "mypage" && <MyPage onNavigate={handleNavigate} />}

          {currentPage === "all-comments" && (
            <AllCommentsPage onNavigate={handleNavigate} />
          )}

          {currentPage === "profile-edit" && (
            <ProfileEditPage onNavigate={handleNavigate} />
          )}
        </div>
      </div>
    </>
  );
};

export default App;
