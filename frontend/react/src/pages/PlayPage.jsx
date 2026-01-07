/**
 * 놀이 페이지
 * 추후 WebGL 게임이 들어갈 예정
 */

const PlayPage = ({ onNavigate }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "calc(100vh - 76px)",
        backgroundColor: "#000000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#ffffff",
        fontSize: "24px",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <h1 style={{ marginBottom: "20px" }}>놀이 페이지</h1>
        <p style={{ opacity: 0.7 }}>WebGL 게임이 곧 추가될 예정입니다.</p>
      </div>
    </div>
  );
};

export default PlayPage;
