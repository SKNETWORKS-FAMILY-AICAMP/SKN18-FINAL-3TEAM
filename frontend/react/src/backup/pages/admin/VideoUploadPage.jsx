import { useState } from "react";
import { COLORS } from "../../constants/theme";

const VideoUploadPage = () => {
  const [title, setTitle] = useState("");
  const [videoFile, setVideoFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [tags, setTags] = useState([""]);
  const [uploadMethod, setUploadMethod] = useState("file");
  const [thumbnailFile, setThumbnailFile] = useState(null);
  const [thumbnailPreview, setThumbnailPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

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
        const formData = new FormData();
        formData.append("title", title.trim());
        formData.append("video_file", videoFile);

        if (thumbnailFile) {
          formData.append("thumbnail_file", thumbnailFile);
        }

        const tagArray = tags.filter((tag) => tag.trim() !== "");
        tagArray.forEach((tag) => {
          formData.append("tags[]", tag.trim());
        });

        response = await fetch("http://localhost:8000/api/video/upload/", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } else {
        const requestData = {
          title: title.trim(),
          video_url: videoUrl.trim(),
          tags: tags
            .filter((tag) => tag.trim() !== "")
            .map((tag) => tag.trim()),
        };

        if (thumbnailFile) {
          const formData = new FormData();
          formData.append("title", title.trim());
          formData.append("video_url", videoUrl.trim());
          formData.append("thumbnail_file", thumbnailFile);
          const tagArray = tags.filter((tag) => tag.trim() !== "");
          tagArray.forEach((tag) => {
            formData.append("tags[]", tag.trim());
          });
          response = await fetch("http://localhost:8000/api/video/upload/", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: formData,
          });
        } else {
          response = await fetch("http://localhost:8000/api/video/upload/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(requestData),
          });
        }
      }

      const data = await response.json();

      if (response.ok) {
        setMessage({
          type: "success",
          text: "영상이 성공적으로 추가되었습니다!",
        });
        setTitle("");
        setVideoFile(null);
        setVideoUrl("");
        setTags([""]);
        setThumbnailFile(null);
        setThumbnailPreview(null);
        const fileInput = document.getElementById("video-file-input");
        if (fileInput) fileInput.value = "";
        const thumbnailInput = document.getElementById("thumbnail-file-input");
        if (thumbnailInput) thumbnailInput.value = "";
      } else {
        setMessage({
          type: "error",
          text:
            data.error?.message || data.message || "영상 추가에 실패했습니다.",
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
    <div>
      <div
        style={{
          backgroundColor: "transparent",
          padding: "40px",
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
            <div
              style={{
                position: "relative",
                width: "400px",
                aspectRatio: "16/9",
                backgroundColor: COLORS.lightGray,
                borderRadius: "12px",
                border: "2px dashed #ccc",
                overflow: "hidden",
                cursor: "pointer",
                transition: "transform 0.3s ease, border-color 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "scale(1.01)";
                e.currentTarget.style.borderColor = COLORS.primary;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "scale(1)";
                e.currentTarget.style.borderColor = "#ccc";
              }}
              onClick={() => {
                const input = document.getElementById("thumbnail-file-input");
                if (input) input.click();
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
                  }}
                >
                  <button
                    type="button"
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
                    Choose file
                  </button>
                </div>
              )}
              <input
                id="thumbnail-file-input"
                type="file"
                accept="image/*"
                onChange={handleThumbnailChange}
                style={{
                  position: "absolute",
                  width: "100%",
                  height: "100%",
                  opacity: 0,
                  cursor: "pointer",
                }}
              />
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
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: "100%",
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
            {isSubmitting ? "추가 중..." : "영상 추가"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default VideoUploadPage;
