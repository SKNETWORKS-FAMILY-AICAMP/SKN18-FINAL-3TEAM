import { useState, useEffect, useRef } from "react";
import { COLORS } from "../constants/theme";
import {
  UserIcon,
  ArrowLeftIcon,
  CameraIcon,
} from "../components/common/Icons";
import { checkAuth } from "../api/authApi";
import api from "../api/axios";
import { getProfileImageUrl } from "../utils/imageUtils";

const ProfileEditPage = ({ onNavigate, user: initialUser, onUserUpdate }) => {
  const [user, setUser] = useState(initialUser || null);
  const [formData, setFormData] = useState({
    nickname: "",
    email: "",
    gender: null,
    age: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const fileInputRef = useRef(null);

  // 성별 값 정규화 (undefined -> null, true/false 유지)
  const normalizeGender = (value) => {
    if (value === true || value === false) return value;
    return null;
  };

  // 사용자 프로필 데이터 로드 - 항상 API에서 최신 데이터 가져오기
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await api.get("/api/users/profile/");
        const profileData = response.data.data;
        console.log("프로필 데이터 로드:", profileData);
        console.log(
          "성별 값:",
          profileData.gender,
          "타입:",
          typeof profileData.gender
        );
        setUser(profileData);
        setFormData({
          nickname: profileData.nickname || "",
          email: profileData.email || "",
          gender: normalizeGender(profileData.gender),
          age: profileData.age ?? null,
        });
      } catch (error) {
        console.error("프로필 로드 실패:", error);
        // API 실패 시 initialUser로 fallback
        if (initialUser) {
          setUser(initialUser);
          setFormData({
            nickname: initialUser.nickname || "",
            email: initialUser.email || "",
            gender: normalizeGender(initialUser.gender),
            age: initialUser.age ?? null,
          });
        }
      } finally {
        setLoading(false);
      }
    };

    // 항상 API에서 최신 데이터 로드
    loadProfile();
  }, []);

  const handleImageChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 파일 타입 검증
    if (!file.type.startsWith("image/")) {
      alert("이미지 파일만 업로드 가능합니다.");
      return;
    }

    // 파일 크기 검증 (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert("이미지 크기는 5MB 이하여야 합니다.");
      return;
    }

    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append("image", file);

      // FormData를 사용할 때는 Content-Type을 명시하지 않음 (브라우저가 자동으로 boundary 설정)
      const response = await api.post("/api/users/profile/image/", formData);

      if (response.data.data) {
        // 프로필 이미지 업데이트
        const updatedUser = {
          ...user,
          profile_image: response.data.data.image_url,
        };
        setUser(updatedUser);
        // 부모 컴포넌트(App.jsx)의 user 상태 업데이트
        if (onUserUpdate) {
          onUserUpdate(updatedUser);
        }
        alert("프로필 이미지가 업로드되었습니다.");
      }
    } catch (error) {
      console.error("이미지 업로드 실패:", error);
      console.error("에러 상세:", {
        status: error.response?.status,
        data: error.response?.data,
        headers: error.config?.headers,
        url: error.config?.url,
      });

      if (error.response?.status === 403) {
        const token = localStorage.getItem("access_token");
        console.error(
          "현재 토큰:",
          token ? token.substring(0, 20) + "..." : "없음"
        );
        alert("권한이 없습니다. 다시 로그인해주세요.");
      } else if (error.response?.data?.error?.fields) {
        const fields = error.response.data.error.fields;
        const firstError = Object.values(fields)[0];
        if (Array.isArray(firstError)) {
          alert(firstError[0]);
        } else {
          alert(firstError);
        }
      } else {
        alert("이미지 업로드에 실패했습니다.");
      }
    } finally {
      setUploadingImage(false);
      // 파일 input 초기화
      if (e.target) {
        e.target.value = "";
      }
    }
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "정말 탈퇴하시겠습니까? 탈퇴 시 모든 데이터가 삭제되며 복구할 수 없습니다."
    );

    if (!confirmed) return;

    try {
      await api.delete("/api/users/delete-account/");
      // 토큰 삭제
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      alert("회원 탈퇴가 완료되었습니다.");
      // 메인 페이지로 이동 및 새로고침
      window.location.href = "/";
    } catch (error) {
      console.error("회원 탈퇴 실패:", error);
      alert("회원 탈퇴에 실패했습니다. 다시 시도해주세요.");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // 성별 값 정규화 (undefined -> null로 변환)
      const normalizedGender = normalizeGender(formData.gender);

      // 빈 문자열을 null로 변환
      const payload = {
        nickname: formData.nickname?.trim() || null,
        gender: normalizedGender, // null, true, false 중 하나
        age: formData.age ?? null,
      };

      console.log("프로필 수정 요청:", payload);
      console.log("성별 값:", {
        원본: formData.gender,
        정규화: normalizedGender,
        타입: typeof normalizedGender,
      });
      const token = localStorage.getItem("access_token");
      console.log(
        "사용 중인 토큰:",
        token ? token.substring(0, 20) + "..." : "없음"
      );

      const response = await api.patch("/api/users/profile/", payload);

      // 성공 시 사용자 정보 업데이트
      if (response.data.data) {
        console.log("프로필 수정 응답:", response.data.data);
        console.log("저장된 성별 값:", {
          값: response.data.data.gender,
          타입: typeof response.data.data.gender,
        });
        setUser(response.data.data);
        // 부모 컴포넌트(App.jsx)의 user 상태 즉시 업데이트
        if (onUserUpdate) {
          onUserUpdate(response.data.data);
        }
        // 스크롤을 맨 위로 이동
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
        // 마이페이지로 돌아가기
        onNavigate("mypage");
      }
    } catch (error) {
      console.error("프로필 수정 실패:", error);
      console.error("에러 상세:", {
        status: error.response?.status,
        data: error.response?.data,
        headers: error.config?.headers,
      });

      if (error.response?.status === 403) {
        alert("권한이 없습니다. 다시 로그인해주세요.");
      } else if (error.response?.data?.error?.fields) {
        const fields = error.response.data.error.fields;
        const firstError = Object.values(fields)[0];
        if (Array.isArray(firstError)) {
          alert(firstError[0]);
        } else {
          alert(firstError);
        }
      } else if (error.response?.data?.error?.message) {
        alert(error.response.data.error.message);
      } else {
        alert("프로필 수정에 실패했습니다.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          padding: "50px 60px",
          backgroundColor: COLORS.background,
          minHeight: "calc(100vh - 76px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ fontSize: "16px", color: COLORS.dark }}>로딩 중...</div>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "50px 60px",
        backgroundColor: COLORS.background,
        minHeight: "calc(100vh - 76px)",
      }}
    >
      <button
        onClick={() => onNavigate("mypage")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "14px",
          color: COLORS.dark,
          marginBottom: "40px",
        }}
      >
        <ArrowLeftIcon size={18} color={COLORS.dark} />
        마이페이지로 돌아가기
      </button>

      <div style={{ maxWidth: "600px", margin: "0 auto" }}>
        <h1
          style={{
            fontSize: "32px",
            fontWeight: "800",
            color: COLORS.dark,
            marginBottom: "50px",
          }}
        >
          프로필 수정
        </h1>

        <div style={{ textAlign: "center", marginBottom: "50px" }}>
          <div
            style={{
              width: "140px",
              height: "140px",
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
              margin: "0 auto 16px",
              position: "relative",
            }}
          >
            {!user?.profile_image && (
              <UserIcon size={70} color={COLORS.white} />
            )}
            <label
              style={{
                position: "absolute",
                bottom: "0",
                right: "0",
                width: "42px",
                height: "42px",
                borderRadius: "50%",
                backgroundColor: COLORS.cardCream,
                border: `3px solid ${COLORS.background}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: uploadingImage ? "wait" : "pointer",
                opacity: uploadingImage ? 0.6 : 1,
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                style={{ display: "none" }}
                disabled={uploadingImage}
              />
              <CameraIcon size={20} color={COLORS.dark} />
            </label>
          </div>
          <span style={{ fontSize: "13px", color: COLORS.dark }}>
            프로필 사진 변경
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
          {/* 닉네임 */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "700",
                color: COLORS.dark,
                marginBottom: "10px",
              }}
            >
              닉네임
            </label>
            <input
              type="text"
              value={formData.nickname}
              onChange={(e) =>
                setFormData({ ...formData, nickname: e.target.value })
              }
              style={{
                width: "100%",
                padding: "16px 20px",
                border: "none",
                borderRadius: "12px",
                fontSize: "16px",
                backgroundColor: COLORS.cardCream,
                color: COLORS.dark,
                outline: "none",
              }}
              onFocus={(e) => {
                e.target.style.boxShadow = `0 0 0 3px ${COLORS.primary}`;
              }}
              onBlur={(e) => {
                e.target.style.boxShadow = "none";
              }}
            />
          </div>

          {/* 이메일 (수정 불가) */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "700",
                color: COLORS.dark,
                marginBottom: "10px",
              }}
            >
              이메일 (수정 불가)
            </label>
            <input
              type="email"
              value={formData.email}
              disabled
              style={{
                width: "100%",
                padding: "16px 20px",
                border: "none",
                borderRadius: "12px",
                fontSize: "16px",
                backgroundColor: COLORS.lightGray,
                color: COLORS.dark,
                outline: "none",
                cursor: "not-allowed",
                opacity: 0.6,
              }}
            />
          </div>

          {/* 성별 */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "700",
                color: COLORS.dark,
                marginBottom: "10px",
              }}
            >
              성별
            </label>
            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={() => setFormData({ ...formData, gender: true })}
                style={{
                  flex: 1,
                  padding: "16px 20px",
                  border: `2px solid ${
                    formData.gender === true ? COLORS.primary : COLORS.lightGray
                  }`,
                  borderRadius: "12px",
                  fontSize: "16px",
                  backgroundColor:
                    formData.gender === true ? COLORS.primary : "transparent",
                  color: COLORS.dark,
                  cursor: "pointer",
                  fontWeight: formData.gender === true ? "700" : "500",
                }}
              >
                남성
              </button>
              <button
                onClick={() => setFormData({ ...formData, gender: false })}
                style={{
                  flex: 1,
                  padding: "16px 20px",
                  border: `2px solid ${
                    formData.gender === false
                      ? COLORS.primary
                      : COLORS.lightGray
                  }`,
                  borderRadius: "12px",
                  fontSize: "16px",
                  backgroundColor:
                    formData.gender === false ? COLORS.primary : "transparent",
                  color: COLORS.dark,
                  cursor: "pointer",
                  fontWeight: formData.gender === false ? "700" : "500",
                }}
              >
                여성
              </button>
              <button
                onClick={() => setFormData({ ...formData, gender: null })}
                style={{
                  flex: 1,
                  padding: "16px 20px",
                  border: `2px solid ${
                    formData.gender === null ? COLORS.primary : COLORS.lightGray
                  }`,
                  borderRadius: "12px",
                  fontSize: "16px",
                  backgroundColor:
                    formData.gender === null ? COLORS.primary : "transparent",
                  color: COLORS.dark,
                  cursor: "pointer",
                  fontWeight: formData.gender === null ? "700" : "500",
                }}
              >
                선택 안함
              </button>
            </div>
          </div>

          {/* 나이 */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "700",
                color: COLORS.dark,
                marginBottom: "10px",
              }}
            >
              나이
            </label>
            <input
              type="number"
              min="0"
              max="120"
              value={formData.age || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  age: e.target.value ? parseInt(e.target.value) : null,
                })
              }
              placeholder="나이를 입력하세요"
              style={{
                width: "100%",
                padding: "16px 20px",
                border: "none",
                borderRadius: "12px",
                fontSize: "16px",
                backgroundColor: COLORS.cardCream,
                color: COLORS.dark,
                outline: "none",
              }}
              onFocus={(e) => {
                e.target.style.boxShadow = `0 0 0 3px ${COLORS.primary}`;
              }}
              onBlur={(e) => {
                e.target.style.boxShadow = "none";
              }}
            />
          </div>
        </div>

        <div style={{ display: "flex", gap: "16px", marginTop: "50px" }}>
          <button
            onClick={() => onNavigate("mypage")}
            style={{
              flex: 1,
              padding: "16px 28px",
              border: `2px solid ${COLORS.lightGray}`,
              borderRadius: "12px",
              backgroundColor: "transparent",
              fontSize: "16px",
              fontWeight: "600",
              cursor: "pointer",
              color: COLORS.dark,
            }}
          >
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              flex: 1,
              padding: "16px 28px",
              border: "none",
              borderRadius: "12px",
              backgroundColor: saving ? COLORS.lightGray : COLORS.primary,
              fontSize: "16px",
              fontWeight: "700",
              cursor: saving ? "not-allowed" : "pointer",
              color: COLORS.dark,
              transition: "transform 0.2s",
            }}
            onMouseEnter={(e) => {
              if (!saving) {
                e.currentTarget.style.transform = "scale(1.02)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            {saving ? "저장 중..." : "저장하기"}
          </button>
        </div>

        {/* 탈퇴하기 버튼 */}
        <div
          style={{
            marginTop: "60px",
            paddingTop: "30px",
            borderTop: `1px solid ${COLORS.lightGray}`,
          }}
        >
          <button
            onClick={handleDeleteAccount}
            style={{
              width: "100%",
              padding: "14px 28px",
              border: "none",
              borderRadius: "12px",
              backgroundColor: "transparent",
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              color: "#e63946",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(230, 57, 70, 0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            회원 탈퇴
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileEditPage;
