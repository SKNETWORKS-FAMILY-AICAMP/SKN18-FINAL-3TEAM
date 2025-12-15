/**
 * Header Component - history-contents-app-2.jsx 스타일 완전 복사
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../features/auth";
import "./Header.css";

const COLORS = {
  primary: '#cffd1e',
  tag: '#7286ff',
  dark: '#1a1a1a',
  gray: '#666666',
  lightGray: '#e8e8e8',
  white: '#ffffff',
  overlay: 'rgba(80, 80, 80, 0.95)',
};

// 로고 아이콘
const LogoIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="18" cy="18" r="14" fill="#c8e0ff" />
    <path d="M28 12 C38 12, 42 20, 42 28 C42 36, 36 42, 28 42 C20 42, 18 38, 18 32"
          fill={COLORS.primary} stroke="none"/>
    <circle cx="28" cy="42" r="5" fill="#333" />
  </svg>
);

// 검색 아이콘
const SearchIcon = ({ color = "#333" }: { color?: string }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
);

// 유저 아이콘
const UserIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2">
    <circle cx="12" cy="8" r="4"/>
    <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>
  </svg>
);

export function Header() {
  const [language, setLanguage] = useState("ko");
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

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
        <div onClick={() => navigate("/")} style={{ cursor: 'pointer' }}>
          <LogoIcon />
        </div>
        <div onClick={() => navigate("/")} style={{
          fontSize: '14px',
          fontWeight: '600',
          lineHeight: '1.3',
          color: COLORS.dark,
          cursor: 'pointer',
        }}>
          History &<br />Contents
        </div>
      </div>

      {/* 검색 버튼 (클릭 시 확장) */}
      <div
        onClick={() => navigate("/search")}
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
            backgroundColor: language === 'ko' ? '#f5f5f5' : 'transparent',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: '500',
          }}
          onClick={() => setLanguage('ko')}
          >한</button>
          <button style={{
            padding: '8px 14px',
            border: 'none',
            backgroundColor: language === 'en' ? '#f5f5f5' : 'transparent',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: '500',
          }}
          onClick={() => setLanguage('en')}
          >EN</button>
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
            <span>{isAuthenticated ? '사용자' : '로그인'}</span>
          </button>

          {isAuthenticated && showUserDropdown && (
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
              <div
                onClick={() => navigate("/profile")}
                style={{
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
}
