import { COLORS } from "../../../constants/theme";

const PopularTags = ({ tags, onTagClick, contentVisible }) => {
  return (
    <div>
      <h3
        style={{
          fontSize: "15px",
          fontWeight: "700",
          color: COLORS.dark,
          marginBottom: "20px",
          letterSpacing: "0.5px",
        }}
      >
        인기 태그
      </h3>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        {tags.map((tag, idx) => (
          <button
            key={idx}
            onClick={() => onTagClick(tag)}
            style={{
              padding: "10px 20px",
              backgroundColor: COLORS.sky,
              border: "none",
              borderRadius: "25px",
              color: COLORS.dark,
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "all 0.2s ease",
              opacity: contentVisible ? 1 : 0,
              transform: contentVisible ? "translateY(0)" : "translateY(10px)",
              transitionDelay: `${0.2 + idx * 0.03}s`,
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = "#a8d4f0";
              e.target.style.transform = "scale(1.05)";
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = COLORS.sky;
              e.target.style.transform = "scale(1)";
            }}
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  );
};

export default PopularTags;
