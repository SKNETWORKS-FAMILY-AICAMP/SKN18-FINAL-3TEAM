import { useState } from "react";
import { COLORS } from "../constants/theme";
import { ArrowLeftIcon } from "../components/common/Icons";
import VideoManagementPage from "./admin/VideoManagementPage";
import UserManagementPage from "./admin/UserManagementPage";

const AdminPage = ({ onNavigate, user }) => {
  const [activeSection, setActiveSection] = useState("video");

  const handleVideoClick = (videoId) => {
    onNavigate("video", videoId);
  };

  return (
    <div
      style={{
        display: "flex",
        minHeight: "calc(100vh - 76px)",
        backgroundColor: COLORS.background,
      }}
    >
      {/* 좌측 사이드바 */}
      <div
        style={{
          width: "240px",
          padding: "60px 40px",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => onNavigate("main")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "14px",
            color: COLORS.textSecondary,
            marginBottom: "48px",
            padding: 0,
          }}
        >
          <ArrowLeftIcon size={18} color={COLORS.textSecondary} />
          메인으로 돌아가기
        </button>

        {/* 영상 관리하기 */}
        <div
          onClick={() => setActiveSection("video")}
          style={{
            fontSize: "16px",
            fontWeight: "600",
            color: activeSection === "video" ? COLORS.textPrimary : COLORS.gray,
            cursor: "pointer",
            padding: "8px 0",
            marginBottom: "24px",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => {
            if (activeSection !== "video") {
              e.currentTarget.style.color = COLORS.textPrimary;
            }
          }}
          onMouseLeave={(e) => {
            if (activeSection !== "video") {
              e.currentTarget.style.color = COLORS.gray;
            }
          }}
        >
          영상 관리하기
        </div>

        {/* 사용자 관리하기 */}
        <div
          onClick={() => setActiveSection("user")}
          style={{
            fontSize: "16px",
            fontWeight: "600",
            color: activeSection === "user" ? COLORS.textPrimary : COLORS.gray,
            cursor: "pointer",
            padding: "8px 0",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => {
            if (activeSection !== "user") {
              e.currentTarget.style.color = COLORS.textPrimary;
            }
          }}
          onMouseLeave={(e) => {
            if (activeSection !== "user") {
              e.currentTarget.style.color = COLORS.gray;
            }
          }}
        >
          사용자 관리하기
        </div>
      </div>

      {/* 우측 컨텐츠 영역 */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {activeSection === "video" && (
          <VideoManagementPage onVideoClick={handleVideoClick} />
        )}
        {activeSection === "user" && <UserManagementPage />}
      </div>
    </div>
  );
};

export default AdminPage;
