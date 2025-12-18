import { useState, useEffect, useRef } from "react";
import { COLORS } from "../../constants/theme";
import { SearchIcon, UserIcon, GlobeIcon } from "../common/Icons";
import { getProfileImageUrl } from "../../utils/imageUtils";

// 글라스 효과 스타일
const glassStyle = {
  background: "rgba(255, 255, 255, 0.7)",
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  border: "1px solid rgba(255, 255, 255, 0.3)",
  boxShadow: "0 2px 8px rgba(0, 0, 0, 0.06)",
};

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
}) => {
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const langDropdownRef = useRef(null);
  const userDropdownRef = useRef(null);
  const langButtonRef = useRef(null);
  const userButtonRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setIsScrolled(scrollY > 50);
    };

    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        showLangDropdown &&
        langDropdownRef.current &&
        langButtonRef.current &&
        !langDropdownRef.current.contains(event.target) &&
        !langButtonRef.current.contains(event.target)
      ) {
        setShowLangDropdown(false);
      }
      if (
        showUserDropdown &&
        userDropdownRef.current &&
        userButtonRef.current &&
        !userDropdownRef.current.contains(event.target) &&
        !userButtonRef.current.contains(event.target)
      ) {
        setShowUserDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showLangDropdown, showUserDropdown, setShowUserDropdown]);

  return (
    <>
      <header
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          width: "100%",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: isScrolled ? "12px 60px" : "20px 60px",
          background: "transparent",
          pointerEvents: "none",
          transition: "padding 0.3s ease",
          boxSizing: "border-box",
        }}
      >
        {/* 로고 */}
        <div
          onClick={onLogoClick}
          style={{
            cursor: "pointer",
            pointerEvents: "auto",
            transition: "all 0.3s ease",
          }}
        >
          <div
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: isScrolled ? "24px" : "56px",
              fontWeight: "700",
              lineHeight: isScrolled ? "1.2" : "2.0",
              color: COLORS.dark,
              letterSpacing: "-0.085em",
              textTransform: "uppercase",
              transition: "all 0.3s ease",
            }}
          >
            HISTOK
          </div>
        </div>

        {/* 검색창 - 글라스 효과 */}
        <div
          onClick={onSearchClick}
          style={{
            flex: 1,
            maxWidth: "500px",
            margin: "0 40px",
            position: "relative",
            cursor: "pointer",
            pointerEvents: "auto",
            ...glassStyle,
            borderRadius: "28px",
            padding: "12px 50px 12px 20px",
            transition: "all 0.3s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.85)";
            e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.1)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.7)";
            e.currentTarget.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.06)";
          }}
        >
          <span style={{ fontSize: "14px", color: "#999" }}>
            검색어를 입력하세요
          </span>
          <div
            style={{
              position: "absolute",
              right: "6px",
              top: "50%",
              transform: "translateY(-50%)",
              width: "34px",
              height: "34px",
              borderRadius: "50%",
              backgroundColor: COLORS.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <SearchIcon size={16} />
          </div>
        </div>

        {/* 오른쪽 버튼들 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            pointerEvents: "auto",
          }}
        >
          {/* 언어 선택 버튼 - 글라스 효과 */}
          <div style={{ position: "relative" }}>
            <button
              ref={langButtonRef}
              onClick={() => setShowLangDropdown(!showLangDropdown)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "42px",
                height: "42px",
                ...glassStyle,
                borderRadius: "12px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                border: "none",
                padding: 0,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.9)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.7)";
              }}
            >
              <GlobeIcon size={22} color="#333" />
            </button>
          </div>

          {/* 사용자 버튼 또는 로그인 버튼 */}
          {isLoggedIn ? (
            <div style={{ position: "relative" }}>
              <button
                ref={userButtonRef}
                onClick={() => setShowUserDropdown(!showUserDropdown)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "6px 16px 6px 6px",
                  ...glassStyle,
                  borderRadius: "24px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.9)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.7)";
                }}
              >
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "50%",
                    backgroundColor: user?.profile_image
                      ? "transparent"
                      : COLORS.primary,
                    backgroundImage: user?.profile_image
                      ? `url(${getProfileImageUrl(user.profile_image)})`
                      : "none",
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {!user?.profile_image && <UserIcon size={16} />}
                </div>
                <span
                  style={{
                    fontSize: "14px",
                    fontWeight: "500",
                    color: COLORS.dark,
                  }}
                >
                  {user?.nickname ||
                    user?.display_name ||
                    user?.email?.split("@")[0] ||
                    "사용자"}
                </span>
              </button>
            </div>
          ) : (
            <button
              onClick={onLogin}
              style={{
                padding: "8px 20px",
                ...glassStyle,
                borderRadius: "24px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                fontSize: "14px",
                fontWeight: "600",
                color: COLORS.dark,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.9)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.7)";
              }}
            >
              로그인
            </button>
          )}
        </div>
      </header>

      {/* 언어 드롭다운 */}
      {showLangDropdown && (
        <div
          ref={langDropdownRef}
          style={{
            position: "fixed",
            top: isScrolled ? "60px" : "110px",
            right: "180px",
            background: COLORS.sky,
            borderRadius: "16px",
            padding: "8px 0",
            minWidth: "120px",
            zIndex: 1001,
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
            transition: "top 0.3s ease",
          }}
        >
          <div
            onClick={() => setShowLangDropdown(false)}
            style={{
              padding: "12px 20px",
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            한국어
          </div>
          <div
            onClick={() => setShowLangDropdown(false)}
            style={{
              padding: "12px 20px",
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            English
          </div>
        </div>
      )}

      {/* 사용자 드롭다운 */}
      {isLoggedIn && showUserDropdown && (
        <div
          ref={userDropdownRef}
          style={{
            position: "fixed",
            top: isScrolled ? "60px" : "110px",
            right: "60px",
            background: COLORS.sky,
            borderRadius: "16px",
            padding: "8px 0",
            minWidth: "140px",
            zIndex: 1001,
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
            transition: "top 0.3s ease",
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
                color: COLORS.dark,
                fontSize: "14px",
                fontWeight: "500",
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
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
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            나의 기록
          </div>
          <div
            onClick={onLogout}
            style={{
              padding: "12px 20px",
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            → 로그아웃
          </div>
        </div>
      )}
    </>
  );
};

export default Header;
