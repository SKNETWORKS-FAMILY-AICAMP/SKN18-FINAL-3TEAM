import { useState, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { getVideo, updateVideo } from "../../api/videoApi";
import { getThumbnailUrl } from "../../utils/imageUtils";

const VideoEditPage = ({ videoId }) => {

  const [title, setTitle] = useState("");
  const [videoFile, setVideoFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [tags, setTags] = useState([""]);
  const [uploadMethod, setUploadMethod] = useState("url");
  const [thumbnailFile, setThumbnailFile] = useState(null);
  const [thumbnailPreview, setThumbnailPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);

  // 기존 영상 데이터 로드
  useEffect(() => {
    // videoId가 없으면 관리 페이지로 리다이렉트
    if (!videoId) {
      console.error("videoId가 없습니다.");
      window.location.hash = "admin";
      return;
    }

    const fetchVideo = async () => {
      try {
        setLoading(true);
        const response = await getVideo(videoId);
        const videoData = response.data;

        setTitle(videoData.title || "");
        setVideoUrl(videoData.video_url || "");
        setTags(videoData.tags && videoData.tags.length > 0 ? videoData.tags : [""]);

        if (videoData.thumbnail_url) {
          setThumbnailPreview(getThumbnailUrl(videoData.thumbnail_url));
        }

        // video_url이 있으면 URL 방식으로 설정
        if (videoData.video_url) {
          setUploadMethod("url");
        }
      } catch (error) {
        console.error("영상 로딩 실패:", error);
        setMessage({ type: "error", text: "영상을 불러오는데 실패했습니다." });
      } finally {
        setLoading(false);
      }
    };

    fetchVideo();
  }, [videoId]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith("video/")) {
        setMessage({
          type: "error",
          text: "비디오 파일만 업로드할 수 있습니다.",
        });
        return;
      }
      setVideoFile(file);
      setMessage({ type: "", text: "" });
    }
  };

  const handleThumbnailChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        setMessage({
          type: "error",
          text: "이미지 파일만 업로드할 수 있습니다.",
        });
        return;
      }
      setThumbnailFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setThumbnailPreview(reader.result);
      };
      reader.readAsDataURL(file);
      setMessage({ type: "", text: "" });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!title.trim()) {
      setMessage({ type: "error", text: "제목은 필수입니다." });
      return;
    }

    if (uploadMethod === "file" && !videoFile && !videoUrl) {
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
      const formData = new FormData();
      formData.append("title", title.trim());

      if (uploadMethod === "file" && videoFile) {
        formData.append("video_file", videoFile);
      } else if (uploadMethod === "url") {
        formData.append("video_url", videoUrl.trim());
      }

      if (thumbnailFile) {
        formData.append("thumbnail_file", thumbnailFile);
      }

      const tagArray = tags.filter((tag) => tag.trim() !== "");
      tagArray.forEach((tag) => {
        formData.append("tags[]", tag.trim());
      });

      const response = await updateVideo(videoId, formData);

      if (response) {
        setMessage({
          type: "success",
          text: "영상이 성공적으로 수정되었습니다!",
        });

        // 2초 후 목록 페이지로 이동
        setTimeout(() => {
          window.location.hash = "admin";
        }, 2000);
      }
    } catch (error) {
      console.error("영상 수정 실패:", error);
      setMessage({ type: "error", text: "영상 수정 중 오류가 발생했습니다." });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "60px 80px" }}>
        <div style={{ textAlign: "center", padding: "40px" }}>로딩 중...</div>
      </div>
    );
  }

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
        영상 수정하기
      </h1>

      <div
        style={{
          backgroundColor: COLORS.white,
          padding: "40px",
          borderRadius: "12px",
          border: "1px solid #eee",
        }}
      >
        <form onSubmit={handleSubmit}>
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
                backgroundColor: COLORS.white,
                color: COLORS.dark,
                outline: "none",
                transition: "border-color 0.2s",
                boxSizing: "border-box",
              }}
              onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
              onBlur={(e) => (e.target.style.borderColor = "#ddd")}
            />
          </div>

          {/* 썸네일 */}
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
              썸네일
            </label>
            <div style={{ display: "flex", gap: "16px", alignItems: "flex-end" }}>
              <div
                style={{
                  position: "relative",
                  width: "400px",
                  aspectRatio: "16/9",
                  backgroundColor: COLORS.lightGray,
                  borderRadius: "12px",
                  border: "2px dashed #ccc",
                  overflow: "hidden",
                  flexShrink: 0,
                }}
              >
                {thumbnailPreview ? (
                  <img
                    src={thumbnailPreview}
                    alt="썸네일 미리보기"
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: "100%",
                      height: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "14px",
                      color: COLORS.gray,
                    }}
                  >
                    썸네일 없음
                  </div>
                )}
                <input
                  id="thumbnail-file-input"
                  type="file"
                  accept="image/*"
                  onChange={handleThumbnailChange}
                  style={{ display: "none" }}
                />
              </div>

              <button
                type="button"
                onClick={() => {
                  const input = document.getElementById("thumbnail-file-input");
                  if (input) input.click();
                }}
                style={{
                  padding: "12px 24px",
                  backgroundColor: COLORS.white,
                  border: "1.5px solid #ddd",
                  borderRadius: "8px",
                  color: COLORS.dark,
                  fontSize: "14px",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  height: "fit-content",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = COLORS.primary;
                  e.currentTarget.style.backgroundColor = COLORS.lightGray;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#ddd";
                  e.currentTarget.style.backgroundColor = COLORS.white;
                }}
              >
                썸네일 선택
              </button>
            </div>
          </div>

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
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <input
                  type="radio"
                  name="uploadMethod"
                  value="file"
                  checked={uploadMethod === "file"}
                  onChange={(e) => setUploadMethod(e.target.value)}
                />
                <span style={{ fontSize: "14px", color: COLORS.dark }}>
                  파일 업로드
                </span>
              </label>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <input
                  type="radio"
                  name="uploadMethod"
                  value="url"
                  checked={uploadMethod === "url"}
                  onChange={(e) => setUploadMethod(e.target.value)}
                />
                <span style={{ fontSize: "14px", color: COLORS.dark }}>
                  URL 입력
                </span>
              </label>
            </div>
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
                영상 파일 {videoUrl ? "(선택사항)" : "*"}
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
                  backgroundColor: COLORS.white,
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
                  선택된 파일: {videoFile.name} (
                  {(videoFile.size / 1024 / 1024).toFixed(2)} MB)
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
                  backgroundColor: COLORS.white,
                  color: COLORS.dark,
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
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {tags.map((tag, index) => (
                <div
                  key={index}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <input
                    type="text"
                    value={tag}
                    onChange={(e) => {
                      const newTags = [...tags];
                      newTags[index] = e.target.value;
                      setTags(newTags);
                    }}
                    placeholder="태그 입력"
                    style={{
                      padding: "8px 12px",
                      border: "1.5px solid #ddd",
                      borderRadius: "6px",
                      fontSize: "13px",
                      backgroundColor: COLORS.white,
                      color: COLORS.dark,
                      outline: "none",
                      transition: "border-color 0.2s",
                      boxSizing: "border-box",
                      minWidth: "120px",
                    }}
                    onFocus={(e) =>
                      (e.target.style.borderColor = COLORS.primary)
                    }
                    onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                  />
                  {tags.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newTags = tags.filter((_, i) => i !== index);
                        setTags(newTags.length > 0 ? newTags : [""]);
                      }}
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "6px",
                        border: "1.5px solid #ddd",
                        backgroundColor: COLORS.white,
                        color: COLORS.gray,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "16px",
                        lineHeight: "1",
                        padding: 0,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = "#ff4444";
                        e.currentTarget.style.color = "#ff4444";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = "#ddd";
                        e.currentTarget.style.color = COLORS.gray;
                      }}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={() => setTags([...tags, ""])}
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  border: "1.5px solid #ddd",
                  backgroundColor: COLORS.white,
                  color: COLORS.dark,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "18px",
                  lineHeight: "1",
                  fontWeight: "600",
                  padding: 0,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = COLORS.primary;
                  e.currentTarget.style.backgroundColor = COLORS.primary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#ddd";
                  e.currentTarget.style.backgroundColor = COLORS.white;
                }}
              >
                +
              </button>
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
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              type="button"
              onClick={() => (window.location.hash = "admin")}
              style={{
                flex: 1,
                padding: "14px",
                backgroundColor: COLORS.lightGray,
                border: "none",
                borderRadius: "8px",
                fontSize: "16px",
                fontWeight: "600",
                color: COLORS.dark,
                cursor: "pointer",
                transition: "opacity 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = 0.8)}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = 1)}
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                flex: 2,
                padding: "14px",
                backgroundColor: isSubmitting ? COLORS.lightGray : "#effd9a",
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
              {isSubmitting ? "수정 중..." : "영상 수정"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default VideoEditPage;
