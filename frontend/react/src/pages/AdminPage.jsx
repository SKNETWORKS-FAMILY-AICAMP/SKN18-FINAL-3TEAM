import { useState } from "react";
import { COLORS } from "../constants/theme";
import { ArrowLeftIcon } from "../components/common/Icons";

const AdminPage = ({ onNavigate, user }) => {
    const [title, setTitle] = useState("");
    const [videoFile, setVideoFile] = useState(null);
    const [videoUrl, setVideoUrl] = useState("");
    const [tags, setTags] = useState("");
    const [uploadMethod, setUploadMethod] = useState("file"); // "file" or "url"
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [message, setMessage] = useState({ type: "", text: "" });

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            // 비디오 파일인지 확인
            if (!file.type.startsWith("video/")) {
                setMessage({ type: "error", text: "비디오 파일만 업로드할 수 있습니다." });
                return;
            }
            setVideoFile(file);
            setMessage({ type: "", text: "" });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!title.trim()) {
            setMessage({ type: "error", text: "제목은 필수입니다." });
            return;
        }

        if (uploadMethod === "file" && !videoFile) {
            setMessage({ type: "error", text: "영상 파일을 선택해주세요." });
            return;
        }

        if (uploadMethod === "url" && !videoUrl.trim()) {
            setMessage({ type: "error", text: "영상 URL을 입력해주세요." });
            return;
        }

        setIsSubmitting(true);
        setMessage({ type: "", text: "" });

        try {
            const token = localStorage.getItem("access_token");
            let response;

            if (uploadMethod === "file") {
                // 파일 업로드
                const formData = new FormData();
                formData.append("title", title.trim());
                formData.append("video_file", videoFile);

                // 태그 처리
                if (tags.trim()) {
                    const tagArray = tags.split(",").map((t) => t.trim());
                    tagArray.forEach((tag) => {
                        formData.append("tags[]", tag);
                    });
                }

                response = await fetch("http://localhost:8000/api/video/upload/", {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                    body: formData,
                });
            } else {
                // URL 입력
                response = await fetch("http://localhost:8000/api/video/upload/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        title: title.trim(),
                        video_url: videoUrl.trim(),
                        tags: tags.trim() ? tags.split(",").map((t) => t.trim()) : [],
                    }),
                });
            }

            const data = await response.json();

            if (response.ok) {
                setMessage({ type: "success", text: "영상이 성공적으로 추가되었습니다!" });
                // 폼 초기화
                setTitle("");
                setVideoFile(null);
                setVideoUrl("");
                setTags("");
                // 파일 input 초기화
                const fileInput = document.getElementById("video-file-input");
                if (fileInput) fileInput.value = "";
            } else {
                setMessage({
                    type: "error",
                    text: data.error?.message || data.message || "영상 추가에 실패했습니다.",
                });
            }
        } catch (error) {
            console.error("영상 추가 실패:", error);
            setMessage({ type: "error", text: "영상 추가 중 오류가 발생했습니다." });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div style={{ padding: "60px 60px", minHeight: "calc(100vh - 76px)" }}>
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
                    marginBottom: "40px",
                }}
            >
                <ArrowLeftIcon size={18} color={COLORS.textSecondary} />
                메인으로 돌아가기
            </button>

            <div style={{ maxWidth: "800px", margin: "0 auto" }}>
                <h1
                    style={{
                        fontSize: "32px",
                        fontWeight: "800",
                        color: COLORS.textPrimary,
                        marginBottom: "40px",
                    }}
                >
                    영상 추가 (Admin)
                </h1>

                <div
                    style={{
                        backgroundColor: COLORS.white,
                        borderRadius: "16px",
                        border: "1px solid #eee",
                        padding: "40px",
                    }}
                >
                    <form onSubmit={handleSubmit}>
                        {/* 업로드 방식 선택 */}
                        <div style={{ marginBottom: "24px" }}>
                            <label
                                style={{
                                    display: "block",
                                    fontSize: "14px",
                                    fontWeight: "600",
                                    color: COLORS.dark,
                                    marginBottom: "12px",
                                }}
                            >
                                업로드 방식
                            </label>
                            <div style={{ display: "flex", gap: "16px" }}>
                                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                                    <input
                                        type="radio"
                                        name="uploadMethod"
                                        value="file"
                                        checked={uploadMethod === "file"}
                                        onChange={(e) => setUploadMethod(e.target.value)}
                                    />
                                    <span style={{ fontSize: "14px", color: COLORS.dark }}>파일 업로드</span>
                                </label>
                                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                                    <input
                                        type="radio"
                                        name="uploadMethod"
                                        value="url"
                                        checked={uploadMethod === "url"}
                                        onChange={(e) => setUploadMethod(e.target.value)}
                                    />
                                    <span style={{ fontSize: "14px", color: COLORS.dark }}>URL 입력</span>
                                </label>
                            </div>
                        </div>

                        {/* 제목 */}
                        <div style={{ marginBottom: "24px" }}>
                            <label
                                style={{
                                    display: "block",
                                    fontSize: "14px",
                                    fontWeight: "600",
                                    color: COLORS.dark,
                                    marginBottom: "8px",
                                }}
                            >
                                영상 제목 *
                            </label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="영상 제목을 입력하세요"
                                style={{
                                    width: "100%",
                                    padding: "12px 16px",
                                    border: "1.5px solid #ddd",
                                    borderRadius: "8px",
                                    fontSize: "14px",
                                    outline: "none",
                                    transition: "border-color 0.2s",
                                    boxSizing: "border-box",
                                }}
                                onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
                                onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                            />
                        </div>

                        {/* 파일 업로드 또는 URL 입력 */}
                        {uploadMethod === "file" ? (
                            <div style={{ marginBottom: "24px" }}>
                                <label
                                    style={{
                                        display: "block",
                                        fontSize: "14px",
                                        fontWeight: "600",
                                        color: COLORS.dark,
                                        marginBottom: "8px",
                                    }}
                                >
                                    영상 파일 *
                                </label>
                                <input
                                    id="video-file-input"
                                    type="file"
                                    accept="video/*"
                                    onChange={handleFileChange}
                                    style={{
                                        width: "100%",
                                        padding: "12px 16px",
                                        border: "1.5px solid #ddd",
                                        borderRadius: "8px",
                                        fontSize: "14px",
                                        outline: "none",
                                        transition: "border-color 0.2s",
                                        boxSizing: "border-box",
                                        cursor: "pointer",
                                    }}
                                    onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
                                    onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                                />
                                {videoFile && (
                                    <div
                                        style={{
                                            fontSize: "12px",
                                            color: COLORS.gray,
                                            marginTop: "6px",
                                        }}
                                    >
                                        선택된 파일: {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(2)} MB)
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div style={{ marginBottom: "24px" }}>
                                <label
                                    style={{
                                        display: "block",
                                        fontSize: "14px",
                                        fontWeight: "600",
                                        color: COLORS.dark,
                                        marginBottom: "8px",
                                    }}
                                >
                                    영상 URL *
                                </label>
                                <input
                                    type="url"
                                    value={videoUrl}
                                    onChange={(e) => setVideoUrl(e.target.value)}
                                    placeholder="https://example.com/video.mp4"
                                    style={{
                                        width: "100%",
                                        padding: "12px 16px",
                                        border: "1.5px solid #ddd",
                                        borderRadius: "8px",
                                        fontSize: "14px",
                                        outline: "none",
                                        transition: "border-color 0.2s",
                                        boxSizing: "border-box",
                                    }}
                                    onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
                                    onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                                />
                            </div>
                        )}

                        {/* 태그 */}
                        <div style={{ marginBottom: "32px" }}>
                            <label
                                style={{
                                    display: "block",
                                    fontSize: "14px",
                                    fontWeight: "600",
                                    color: COLORS.dark,
                                    marginBottom: "8px",
                                }}
                            >
                                태그 (선택사항)
                            </label>
                            <input
                                type="text"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                placeholder="태그1, 태그2, 태그3 (쉼표로 구분)"
                                style={{
                                    width: "100%",
                                    padding: "12px 16px",
                                    border: "1.5px solid #ddd",
                                    borderRadius: "8px",
                                    fontSize: "14px",
                                    outline: "none",
                                    transition: "border-color 0.2s",
                                    boxSizing: "border-box",
                                }}
                                onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
                                onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                            />
                            <div
                                style={{
                                    fontSize: "12px",
                                    color: COLORS.gray,
                                    marginTop: "6px",
                                }}
                            >
                                쉼표(,)로 구분하여 여러 태그를 입력할 수 있습니다
                            </div>
                        </div>

                        {/* 메시지 */}
                        {message.text && (
                            <div
                                style={{
                                    padding: "12px 16px",
                                    borderRadius: "8px",
                                    marginBottom: "24px",
                                    backgroundColor:
                                        message.type === "success" ? "#d4edda" : "#f8d7da",
                                    color: message.type === "success" ? "#155724" : "#721c24",
                                    fontSize: "14px",
                                }}
                            >
                                {message.text}
                            </div>
                        )}

                        {/* 제출 버튼 */}
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            style={{
                                width: "100%",
                                padding: "14px",
                                backgroundColor: isSubmitting ? COLORS.lightGray : COLORS.primary,
                                border: "none",
                                borderRadius: "8px",
                                fontSize: "16px",
                                fontWeight: "600",
                                color: COLORS.dark,
                                cursor: isSubmitting ? "not-allowed" : "pointer",
                                transition: "opacity 0.2s",
                            }}
                            onMouseEnter={(e) =>
                                !isSubmitting && (e.currentTarget.style.opacity = 0.8)
                            }
                            onMouseLeave={(e) => (e.currentTarget.style.opacity = 1)}
                        >
                            {isSubmitting ? "추가 중..." : "영상 추가"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AdminPage;
