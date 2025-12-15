import VideoCard from "./VideoCard";

const VideoGrid = ({ videos, onVideoClick }) => {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "30px",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {videos.map((video) => (
        <VideoCard key={video.id} video={video} onClick={onVideoClick} />
      ))}
    </div>
  );
};

export default VideoGrid;
