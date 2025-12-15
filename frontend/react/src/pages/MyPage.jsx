import UserProfile from "../features/user/components/UserProfile";
import WatchHistory from "../features/user/components/WatchHistory";
import UserComments from "../features/user/components/UserComments";
import UserAnalytics from "../features/user/components/UserAnalytics";

const MyPage = ({ onNavigate }) => {
  const watchHistory = [
    { id: 1, title: "제목" },
    { id: 2, title: "제목" },
    { id: 3, title: "제목" },
    { id: 4, title: "제목" },
  ];

  return (
    <div
      style={{
        display: "flex",
        gap: "40px",
        padding: "60px 60px 40px 60px",
        minHeight: "calc(100vh - 76px)",
      }}
    >
      <UserProfile onEdit={() => onNavigate("profile-edit")} />

      <div style={{ flex: 1 }}>
        <WatchHistory items={watchHistory} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "40px",
            marginTop: "40px",
          }}
        >
          <UserComments onViewAll={() => onNavigate("all-comments")} />
          <UserAnalytics />
        </div>
      </div>
    </div>
  );
};

export default MyPage;
