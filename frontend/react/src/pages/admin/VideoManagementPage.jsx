import { useState } from "react";
import { COLORS } from "../../constants/theme";
import VideoListPage from "./VideoListPage";
import VideoUploadPage from "./VideoUploadPage";

const VideoManagementPage = ({ onVideoClick }) => {
    const [expandedSection, setExpandedSection] = useState(null); // null, "list", "upload"

    const toggleSection = (section) => {
        setExpandedSection(expandedSection === section ? null : section);
    };

    return (
        <div style={{ padding: "60px 80px" }}>
            <h1
                style={{
                    fontSize: "32px",
                    fontWeight: "700",
                    color: COLORS.dark,
                    marginBottom: "48px",
                }}
            >
                영상 관리하기
            </h1>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* 업로드된 영상 아코디언 */}
                <div
                    style={{
                        backgroundColor: COLORS.tertiary, // 연한 베이지
                        borderRadius: "12px",
                        overflow: "hidden",
                        transition: "all 0.3s ease",
                    }}
                >
                    <div
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleSection("list");
                        }}
                        style={{
                            padding: "24px 32px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "16px",
                            backgroundColor: COLORS.tertiary, // 연한 베이지
                            transition: "background-color 0.2s",
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = 0.9;
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = 1;
                        }}
                    >
                        <div
                            style={{
                                width: "32px",
                                height: "32px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "28px",
                                fontWeight: "700",
                                color: COLORS.dark,
                                transition: "transform 0.3s ease",
                                transform: expandedSection === "list" ? "rotate(45deg)" : "rotate(0deg)",
                                flexShrink: 0,
                            }}
                        >
                            {expandedSection === "list" ? "×" : "+"}
                        </div>
                        <div
                            style={{
                                fontSize: "20px",
                                fontWeight: "600",
                                color: COLORS.dark,
                            }}
                        >
                            업로드된 영상
                        </div>
                    </div>
                    <div
                        style={{
                            maxHeight: expandedSection === "list" ? "2000px" : "0",
                            overflow: "hidden",
                            transition: "max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease",
                            opacity: expandedSection === "list" ? 1 : 0,
                        }}
                    >
                        <div style={{ padding: "0 32px 32px 32px" }}>
                            <VideoListPage onVideoClick={onVideoClick} />
                        </div>
                    </div>
                </div>

                {/* 영상 업로드하기 아코디언 */}
                <div
                    style={{
                        backgroundColor: COLORS.secondary, // 하늘색
                        borderRadius: "12px",
                        overflow: "hidden",
                        transition: "all 0.3s ease",
                    }}
                >
                    <div
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleSection("upload");
                        }}
                        style={{
                            padding: "24px 32px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "16px",
                            backgroundColor: COLORS.secondary, // 하늘색
                            transition: "background-color 0.2s",
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = 0.9;
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = 1;
                        }}
                    >
                        <div
                            style={{
                                width: "32px",
                                height: "32px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "28px",
                                fontWeight: "700",
                                color: COLORS.dark,
                                transition: "transform 0.3s ease",
                                transform: expandedSection === "upload" ? "rotate(45deg)" : "rotate(0deg)",
                                flexShrink: 0,
                            }}
                        >
                            {expandedSection === "upload" ? "×" : "+"}
                        </div>
                        <div
                            style={{
                                fontSize: "20px",
                                fontWeight: "600",
                                color: COLORS.dark,
                            }}
                        >
                            영상 업로드하기
                        </div>
                    </div>
                    <div
                        style={{
                            maxHeight: expandedSection === "upload" ? "2000px" : "0",
                            overflow: "hidden",
                            transition: "max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease",
                            opacity: expandedSection === "upload" ? 1 : 0,
                        }}
                    >
                        <div style={{ padding: "0 32px 32px 32px" }}>
                            <VideoUploadPage />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VideoManagementPage;

