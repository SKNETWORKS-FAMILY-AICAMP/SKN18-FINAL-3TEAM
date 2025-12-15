import { COLORS } from "../../../constants/theme";
import { UserIcon } from "../../../components/common/Icons";
import { getProfileImageUrl } from "../../../utils/imageUtils";

const UserProfile = ({ onEdit, user }) => {
  return (
    <div style={{ width: "200px", textAlign: "center" }}>
      <div
        style={{
          width: "160px",
          height: "160px",
          borderRadius: "50%",
          backgroundColor: user?.profile_image ? "transparent" : COLORS.primary,
          backgroundImage: user?.profile_image
            ? `url(${getProfileImageUrl(user.profile_image)})`
            : "none",
          backgroundSize: "cover",
          backgroundPosition: "center",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 20px",
        }}
      >
        {!user?.profile_image && <UserIcon size={80} color={COLORS.white} />}
      </div>
      <div
        style={{
          fontSize: "18px",
          fontWeight: "700",
          color: COLORS.dark,
          marginBottom: "8px",
        }}
      >
        {user?.display_name ||
          user?.nickname ||
          user?.email?.split("@")[0] ||
          "사용자"}
      </div>
      {user?.email && (
        <div
          style={{
            fontSize: "14px",
            color: COLORS.dark,
            opacity: 0.6,
            marginBottom: "20px",
          }}
        >
          {user.email}
        </div>
      )}
      <button
        onClick={onEdit}
        style={{
          padding: "10px 24px",
          border: "2px solid #333",
          borderRadius: "8px",
          backgroundColor: "transparent",
          fontSize: "14px",
          fontWeight: "600",
          cursor: "pointer",
        }}
      >
        수정하기
      </button>
    </div>
  );
};

export default UserProfile;
