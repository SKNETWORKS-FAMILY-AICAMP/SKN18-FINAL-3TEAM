/**
 * 놀이 페이지
 * MinjiRun WebGL 게임
 */

const PlayPage = ({ onNavigate }) => {
  // API URL 가져오기
  const apiUrl = window.ENV?.API_URL || 'https://api.histok.info';
  const gameUrl = `${apiUrl}/game/minjirun/`;

  return (
    <div
      style={{
        width: "100%",
        height: "calc(100vh - 76px)",
        backgroundColor: "#000000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <iframe
        src={gameUrl}
        style={{
          width: "100%",
          height: "100%",
          border: "none",
        }}
        title="MinjiRun Game"
        allow="fullscreen"
      />
    </div>
  );
};

export default PlayPage;
