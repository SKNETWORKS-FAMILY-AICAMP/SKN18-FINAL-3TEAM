import { useState, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { getProfileImageUrl } from "../../utils/imageUtils";
import { UserIcon } from "../common/Icons";

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
  // 프로필 이미지 로딩 실패 시 fallback 표시를 위한 상태
  const [imageError, setImageError] = useState(false);

  // user가 변경되면 imageError 초기화
  useEffect(() => {
    setImageError(false);
  }, [user?.profile_image]);

  const handleNavClick = (page) => {
    if (onNavigate) {
      onNavigate(page);
    }
  };

  const getNavClass = (page) => {
    return currentPage === page ? "active" : "";
  };

  // 프로필 이미지가 유효한지 확인 (이미지가 있고, 로딩 에러가 없는 경우)
  const hasValidProfileImage = user?.profile_image && !imageError;

  return (
    <header className="header">
      <div className="header-logo" onClick={onLogoClick}>
        HisToK
      </div>
      {isLoggedIn && (
        <nav className="header-nav">
          <a
            onClick={() => handleNavClick("about")}
            className={getNavClass("about")}
          >
            아가씨
          </a>
          <a
            onClick={() => handleNavClick("question")}
            className={getNavClass("question")}
          >
            대화하기
          </a>
          <a
            onClick={() => handleNavClick("video-create")}
            className={getNavClass("video-create")}
          >
            이야기 만들기
          </a>
          <a
            onClick={() => handleNavClick("play")}
            className={getNavClass("play")}
          >
            놀이
          </a>
          <a
            onClick={() => handleNavClick("mypage")}
            className={getNavClass("mypage")}
          >
            나의 공간
          </a>
        </nav>
      )}
      <div className="header-right">
        <button className="header-search" onClick={onSearchClick}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke={COLORS.jade}
            strokeWidth="1.5"
            style={{ display: "block" }}
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </button>
        {isLoggedIn ? (
          <div
            className="header-profile"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              backgroundColor: hasValidProfileImage
                ? "transparent"
                : COLORS.primary,
              backgroundImage: hasValidProfileImage
                ? `url(${getProfileImageUrl(user.profile_image)})`
                : "none",
              backgroundSize: "cover",
              backgroundPosition: "center",
              cursor: "pointer",
              transition: "transform 0.2s ease",
              overflow: "hidden",
            }}
            onClick={() => {
              setShowUserDropdown(!showUserDropdown);
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "scale(1.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            {/* 프로필 이미지 로딩 에러 감지용 숨겨진 img 태그 */}
            {user?.profile_image && !imageError && (
              <img
                src={getProfileImageUrl(user.profile_image)}
                alt=""
                style={{ display: "none" }}
                onError={() => setImageError(true)}
              />
            )}
            {/* 프로필 이미지가 없거나 로딩 실패 시 이니셜 표시 */}
            {!hasValidProfileImage && (
              <span
                style={{
                  fontSize: "16px",
                  fontWeight: "600",
                  color: COLORS.dark,
                }}
              >
                {user?.nickname?.[0] ||
                  user?.display_name?.[0] ||
                  user?.email?.[0]?.toUpperCase() ||
                  "U"}
              </span>
            )}
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
            나의 공간
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
