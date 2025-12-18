import { useState, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { getUsers, updateUserPermission, deleteUser } from "../../api/adminApi";
import { getProfileImageUrl } from "../../utils/imageUtils";
import { UserIcon } from "../../components/common/Icons";

const UserManagementPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState({ type: "", text: "" });

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const response = await getUsers();
        if (response?.data) {
          setUsers(response.data);
        }
      } catch (error) {
        console.error("사용자 목록 로딩 실패:", error);
        setUsers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handlePermissionChange = async (userId, newPermission) => {
    try {
      await updateUserPermission(userId, newPermission);
      setUsers((prevUsers) =>
        prevUsers.map((user) =>
          user.id === userId ? { ...user, permission: newPermission } : user
        )
      );
      setMessage({ type: "success", text: "권한이 변경되었습니다." });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    } catch (error) {
      console.error("권한 변경 실패:", error);
      setMessage({ type: "error", text: "권한 변경에 실패했습니다." });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`정말로 ${userEmail} 사용자를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      await deleteUser(userId);
      setUsers((prevUsers) => prevUsers.filter((user) => user.id !== userId));
      setMessage({ type: "success", text: "사용자가 삭제되었습니다." });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    } catch (error) {
      console.error("사용자 삭제 실패:", error);
      setMessage({ type: "error", text: "사용자 삭제에 실패했습니다." });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    } catch (error) {
      return "";
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>로딩 중...</div>
    );
  }

  return (
    <div style={{ padding: "40px" }}>
      <h2
        style={{
          fontSize: "24px",
          fontWeight: "700",
          color: COLORS.dark,
          marginBottom: "32px",
        }}
      >
        사용자 관리하기
      </h2>

      {message.text && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "8px",
            marginBottom: "24px",
            backgroundColor: message.type === "success" ? "#d4edda" : "#f8d7da",
            color: message.type === "success" ? "#155724" : "#721c24",
            fontSize: "14px",
          }}
        >
          {message.text}
        </div>
      )}

      <div
        style={{
          backgroundColor: COLORS.white,
          borderRadius: "16px",
          border: "1px solid #eee",
          padding: "24px",
          overflowX: "auto",
        }}
      >
        {users.length === 0 ? (
          <div
            style={{ textAlign: "center", padding: "40px", color: COLORS.gray }}
          >
            사용자가 없습니다.
          </div>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: "2px solid #eee",
                }}
              >
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  프로필
                </th>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  이메일
                </th>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  닉네임
                </th>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  가입일
                </th>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  권한
                </th>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "center",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: COLORS.dark,
                  }}
                >
                  삭제
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  style={{
                    borderBottom: "1px solid #eee",
                  }}
                >
                  <td style={{ padding: "12px" }}>
                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        borderRadius: "50%",
                        backgroundColor: user.profile_image
                          ? "transparent"
                          : COLORS.lightGray,
                        backgroundImage: user.profile_image
                          ? `url(${getProfileImageUrl(user.profile_image)})`
                          : "none",
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {!user.profile_image && (
                        <UserIcon size={20} color={COLORS.gray} />
                      )}
                    </div>
                  </td>
                  <td
                    style={{
                      padding: "12px",
                      fontSize: "14px",
                      color: COLORS.dark,
                    }}
                  >
                    {user.email}
                  </td>
                  <td
                    style={{
                      padding: "12px",
                      fontSize: "14px",
                      color: COLORS.dark,
                    }}
                  >
                    {user.nickname || "-"}
                  </td>
                  <td
                    style={{
                      padding: "12px",
                      fontSize: "14px",
                      color: COLORS.gray,
                    }}
                  >
                    {formatDate(user.sign_up_date)}
                  </td>
                  <td style={{ padding: "12px" }}>
                    <select
                      value={user.permission || "user"}
                      onChange={(e) =>
                        handlePermissionChange(user.id, e.target.value)
                      }
                      style={{
                        padding: "6px 12px",
                        border: "1.5px solid #ddd",
                        borderRadius: "6px",
                        fontSize: "13px",
                        backgroundColor: COLORS.white,
                        color: COLORS.dark,
                        cursor: "pointer",
                        outline: "none",
                      }}
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td style={{ padding: "12px", textAlign: "center" }}>
                    <button
                      onClick={() => handleDeleteUser(user.id, user.email)}
                      style={{
                        padding: "6px 16px",
                        border: "1.5px solid #ff4444",
                        borderRadius: "6px",
                        fontSize: "13px",
                        backgroundColor: COLORS.white,
                        color: "#ff4444",
                        cursor: "pointer",
                        outline: "none",
                        transition: "all 0.2s",
                        display: "block",
                        margin: "0 auto",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = "#ff4444";
                        e.currentTarget.style.color = COLORS.white;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = COLORS.white;
                        e.currentTarget.style.color = "#ff4444";
                      }}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UserManagementPage;
