import { useState } from "react";
import { COLORS } from "../../constants/theme";
import { getProfileImageUrl } from "../../utils/imageUtils";

const Header = ({
  isLoggedIn,
  user,
  showUserDropdown,
  setShowUserDropdown,
  onSearchClick,
  onLogoClick,
  onMyPageClick,
  onLogin,
  onLogout,
  onAdminClick,
  currentPage,
  onNavigate,
}) => {
  const handleNavClick = (page) => {
    if (onNavigate) {
      onNavigate(page);
    }
  };

  const getNavClass = (page) => {
    return currentPage === page ? "active" : "";
  };

  return (
    <header className="header">
      <div className="header-logo" onClick={onLogoClick}>
        HisToK
      </div>
      <nav className="header-nav">
        <a
          onClick={() => handleNavClick("main")}
          className={getNavClass("main")}
        >
          이야기
        </a>
        <a
          onClick={() => handleNavClick("about")}
          className={getNavClass("about")}
        >
          아가씨
        </a>
        {isLoggedIn && (
          <a
            onClick={() => handleNavClick("video-create")}
            className={getNavClass("video-create")}
          >
            이야기 만들기
          </a>
        )}
        <a
          onClick={() => handleNavClick("question")}
          className={getNavClass("question")}
        >
          묻기
        </a>
        <a
          onClick={() => handleNavClick("mypage")}
          className={getNavClass("mypage")}
        >
          나의 공간
        </a>
      </nav>
      <div className="header-right">
        <button className="header-search" onClick={onSearchClick}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </button>
        {isLoggedIn ? (
          <div
            className="header-profile"
            style={{ display: "flex" }}
            onClick={() => {
              setShowUserDropdown(!showUserDropdown);
            }}
          >
            {user?.nickname?.[0] ||
              user?.display_name?.[0] ||
              user?.email?.[0]?.toUpperCase() ||
              "사용자"}
          </div>
        ) : (
          <button className="header-login" id="loginBtn" onClick={onLogin}>
            LOGIN
          </button>
        )}
      </div>

      {/* 사용자 드롭다운 */}
      {isLoggedIn && showUserDropdown && (
        <div
          style={{
            position: "fixed",
            top: "80px",
            right: "3rem",
            background: COLORS.ink,
            borderRadius: "4px",
            padding: "8px 0",
            minWidth: "140px",
            zIndex: 1001,
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
            border: `1px solid ${COLORS.line}`,
          }}
        >
          {user?.permission === "admin" && (
            <div
              onClick={() => {
                onAdminClick();
                setShowUserDropdown(false);
              }}
              style={{
                padding: "12px 20px",
                color: COLORS.white,
                fontSize: "0.75rem",
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = COLORS.jade;
                e.currentTarget.style.color = COLORS.black;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = COLORS.white;
              }}
            >
              관리하기
            </div>
          )}
          <div
            onClick={() => {
              onMyPageClick();
              setShowUserDropdown(false);
            }}
            style={{
              padding: "12px 20px",
              color: COLORS.white,
              fontSize: "0.75rem",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = COLORS.jade;
              e.currentTarget.style.color = COLORS.black;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = COLORS.white;
            }}
          >
            나의 기록
          </div>
          <div
            onClick={() => {
              onLogout();
              setShowUserDropdown(false);
            }}
            style={{
              padding: "12px 20px",
              color: COLORS.white,
              fontSize: "0.75rem",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = COLORS.jade;
              e.currentTarget.style.color = COLORS.black;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = COLORS.white;
            }}
          >
            로그아웃
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
