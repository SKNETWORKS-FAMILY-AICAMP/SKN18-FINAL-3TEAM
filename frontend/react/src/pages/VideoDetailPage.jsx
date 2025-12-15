import VideoPlayer from "../features/video/components/VideoPlayer";
import VideoInfo from "../features/video/components/VideoInfo";
import CommentSection from "../features/video/components/CommentSection";

const VideoDetailPage = () => {
  const comments = [
    {
      id: 1,
      username: "사용자명",
      text: "해당 사건은 몇년도에 발생하였나요?",
      replies: [
        {
          id: 11,
          username: "안녕하세요 사용자님!",
          text: "해당 사건은 1425년(세종 7년)에 발생한 사건입니다.",
          isAI: true,
        },
      ],
    },
    {
      id: 2,
      username: "사용자명",
      text: "영상이 정말 마음에 들어요",
      replies: [],
    },
  ];

  return (
    <div
      style={{
        display: "flex",
        gap: "30px",
        padding: "60px 60px 30px 60px",
        height: "calc(100vh - 76px)",
        overflow: "hidden",
        boxSizing: "border-box",
      }}
    >
      <div style={{ flex: 1, overflow: "hidden" }}>
        <VideoPlayer />
        <VideoInfo
          tags="#전쟁사 #정조"
          title="가나다라마바사"
          date="2025. 12. 01."
          isLiked={false}
          onLikeClick={() => console.log("Like clicked")}
        />
      </div>

      <CommentSection comments={comments} />
    </div>
  );
};

export default VideoDetailPage;
