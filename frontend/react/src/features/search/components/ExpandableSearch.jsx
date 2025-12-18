import { useState, useEffect, useRef } from "react";
import { COLORS } from "../../../constants/theme";
import {
  SearchIcon,
  CloseIcon,
  LogoIcon,
} from "../../../components/common/Icons";
import {
  getSearchHistory,
  createSearchHistory,
} from "../../../api/activityApi";
import { getPopularTags, getPopularVideos } from "../../../api/videoApi";

const ExpandableSearch = ({ isOpen, onClose, isLoggedIn = false, onSearch, onVideoClick }) => {
  const [searchValue, setSearchValue] = useState("");
  const [phase, setPhase] = useState(0); // 0: closed, 1: expanding width, 2: expanding height, 3: content visible
  const [hasBeenOpened, setHasBeenOpened] = useState(false); // 한 번이라도 열렸는지 추적
  const [shouldRender, setShouldRender] = useState(false); // 실제로 렌더링할지 여부
  const inputRef = useRef(null);

  // API에서 가져온 데이터
  const [searchHistory, setSearchHistory] = useState([]);
  const [tags, setTags] = useState([]);
  const [suggestedVideos, setSuggestedVideos] = useState([]);

  // API에서 데이터 로드
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 인기 태그 로드
        const tagsResponse = await getPopularTags();
        if (tagsResponse?.data) {
          setTags(tagsResponse.data.map((t) => `# ${t.tag}`));
        }

        // 인기 영상 로드
        const videosResponse = await getPopularVideos();
        if (videosResponse?.data) {
          setSuggestedVideos(
            videosResponse.data.map((v) => ({
              id: v.id,
              title: v.title,
              tags: v.tags ? v.tags.map((t) => `#${t}`).join(" ") : "",
            }))
          );
        }

        // 로그인한 경우 검색 기록 로드
        if (isLoggedIn) {
          const historyResponse = await getSearchHistory();
          if (historyResponse?.data) {
            setSearchHistory(historyResponse.data.map((h) => h.search_query));
          }
        }
      } catch (error) {
        console.error("검색 데이터 로드 실패:", error);
      }
    };

    if (isOpen) {
      fetchData();
    }
  }, [isOpen, isLoggedIn]);

  // 검색 실행 시 검색 기록 저장 및 검색 페이지로 이동
  const handleSearch = async () => {
    if (!searchValue.trim()) return;

    try {
      if (isLoggedIn) {
        await createSearchHistory(searchValue.trim());
        // 검색 기록 업데이트
        setSearchHistory((prev) =>
          [
            searchValue.trim(),
            ...prev.filter((h) => h !== searchValue.trim()),
          ].slice(0, 5)
        );
      }
      // 검색 페이지로 이동
      if (onSearch) {
        onSearch(searchValue.trim());
      }
      onClose();
    } catch (error) {
      console.error("검색 기록 저장 실패:", error);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setHasBeenOpened(true);
      setShouldRender(true);
      document.body.style.overflow = "hidden";
      // Phase 0.5: 초기 렌더링 (헤더 검색창 크기)
      setPhase(0.5);
      // Phase 1: 검색창 가로 확장
      setTimeout(() => setPhase(1), 50); // 약간의 딜레이 후 확장 시작
      // Phase 2: 드롭다운 세로 확장
      setTimeout(() => setPhase(2), 300);
      // Phase 3: 콘텐츠 페이드인
      setTimeout(() => {
        setPhase(3);
        inputRef.current?.focus();
      }, 550);
    } else if (hasBeenOpened) {
      // 한 번이라도 열렸을 때만 닫기 애니메이션 실행
      // 역순으로 닫기: 3 -> 2 -> 1 -> 0.5
      setPhase(2); // 먼저 콘텐츠 숨김
      setTimeout(() => setPhase(1), 250); // 세로 축소 (250ms 후)
      setTimeout(() => {
        setPhase(0.5); // 가로 축소 (500ms 후)
        document.body.style.overflow = "";
      }, 500);
      // 가로 축소 애니메이션이 끝난 후 컴포넌트 제거
      setTimeout(() => {
        setShouldRender(false);
      }, 850); // 가로 축소 완료 대기 (300ms transition + 여유)
    }
  }, [isOpen, hasBeenOpened]);

  const handleClose = () => {
    onClose();
  };

  // 초기 로드 시에는 렌더링하지 않음
  if (!shouldRender) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        pointerEvents: phase >= 1 ? "auto" : "none",
      }}
    >
      {/* 어두운 배경 오버레이 */}
      <div
        onClick={handleClose}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          opacity: phase >= 1 ? 1 : 0,
          transition: "opacity 0.3s ease",
        }}
      />

      {/* 검색 패널 컨테이너 */}
      <div
        style={{
          position: "absolute",
          top: "50px",
          left: "50%",
          transform: "translateX(-50%)",
          width: phase >= 1 ? "calc(100% - 48px)" : "600px",
          maxWidth: "1400px",
          transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        {/* 검색창 + 드롭다운 패널 */}
        <div
          style={{
            backgroundColor: COLORS.white,
            borderRadius: "16px",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            overflow: "hidden",
            maxHeight: phase >= 2 ? "520px" : "56px",
            transition: "max-height 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
          {/* 상단 검색바 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              padding: "0 24px",
              height: "56px",
              borderBottom: phase >= 2 ? "1px solid #eee" : "none",
            }}
          >
            <span
              style={{
                fontSize: "15px",
                fontWeight: "600",
                color: COLORS.dark,
                marginRight: "16px",
                whiteSpace: "nowrap",
              }}
            >
              검색
            </span>

            <SearchIcon color="#999" />

            <input
              ref={inputRef}
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="검색어를 입력하세요"
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                fontSize: "15px",
                backgroundColor: "transparent",
                color: COLORS.dark,
                marginLeft: "12px",
              }}
            />

            <button
              onClick={() => setSearchValue("")}
              style={{
                background: "none",
                border: "none",
                fontSize: "13px",
                color: COLORS.gray,
                cursor: "pointer",
                padding: "8px 12px",
                whiteSpace: "nowrap",
              }}
            >
              초기화
            </button>

            <button
              onClick={handleClose}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginLeft: "8px",
              }}
            >
              <CloseIcon size={20} color="#666" />
            </button>
          </div>

          {/* 드롭다운 콘텐츠 영역 */}
          <div
            style={{
              display: "flex",
              padding: "28px 32px",
              gap: "48px",
              opacity: phase >= 3 ? 1 : 0,
              transform: phase >= 3 ? "translateY(0)" : "translateY(-10px)",
              transition: "all 0.3s ease 0.1s",
            }}
          >
            {/* 좌측: 검색 기록 & 태그 (로그인한 경우만 표시) */}
            {isLoggedIn && (
              <div
                style={{
                  flex: "0 0 320px",
                }}
              >
                {/* 검색 기록 */}
                <div style={{ marginBottom: "28px" }}>
                  <h3
                    style={{
                      fontSize: "14px",
                      fontWeight: "700",
                      color: COLORS.dark,
                      marginBottom: "16px",
                    }}
                  >
                    검색 기록
                  </h3>

                  <div style={{ display: "flex", flexDirection: "column" }}>
                    {searchHistory.length === 0 ? (
                      <p style={{ fontSize: "13px", color: COLORS.gray }}>
                        검색 기록이 없습니다.
                      </p>
                    ) : (
                      searchHistory.map((item, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "10px 0",
                            borderBottom: "1px solid #f0f0f0",
                            cursor: "pointer",
                            opacity: phase >= 3 ? 1 : 0,
                            transform:
                              phase >= 3
                                ? "translateX(0)"
                                : "translateX(-15px)",
                            transition: `all 0.3s ease ${0.15 + idx * 0.05}s`,
                          }}
                          onClick={() => {
                            setSearchValue(item);
                            if (onSearch) {
                              onSearch(item);
                            }
                            onClose();
                          }}
                        >
                          <span
                            style={{ fontSize: "13px", color: COLORS.gray }}
                          >
                            {item}
                          </span>
                          <button
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              padding: "2px",
                              opacity: 0.4,
                              transition: "opacity 0.2s",
                            }}
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.opacity = 1)
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.opacity = 0.4)
                            }
                          >
                            <CloseIcon size={12} color="#999" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* 인기 태그 */}
                <div>
                  <h3
                    style={{
                      fontSize: "14px",
                      fontWeight: "700",
                      color: COLORS.dark,
                      marginBottom: "16px",
                    }}
                  >
                    인기 태그
                  </h3>

                  <div
                    style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
                  >
                    {tags.length === 0 ? (
                      <p style={{ fontSize: "13px", color: COLORS.gray }}>
                        태그가 없습니다.
                      </p>
                    ) : (
                      tags.map((tag, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            const tagValue = tag.replace("# ", "");
                            setSearchValue(tagValue);
                            if (onSearch) {
                              onSearch(tagValue);
                            }
                            onClose();
                          }}
                          style={{
                            padding: "8px 16px",
                            backgroundColor: "transparent",
                            border: `1.5px solid ${COLORS.tag}`,
                            borderRadius: "20px",
                            color: COLORS.tag,
                            fontSize: "12px",
                            fontWeight: "500",
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                            opacity: phase >= 3 ? 1 : 0,
                            transform:
                              phase >= 3 ? "translateY(0)" : "translateY(8px)",
                            transitionDelay: `${0.2 + idx * 0.025}s`,
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.backgroundColor = COLORS.sky;
                            e.target.style.color = COLORS.dark;
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.backgroundColor = "transparent";
                            e.target.style.color = COLORS.tag;
                          }}
                        >
                          {tag}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 우측: 추천 영상 */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: "700",
                  color: COLORS.dark,
                  marginBottom: "16px",
                }}
              >
                {searchValue ? `"${searchValue}" 관련 영상` : "추천 영상"}
              </h3>

              <div
                style={{
                  display: "flex",
                  gap: "16px",
                  overflowX: "auto",
                  paddingBottom: "8px",
                }}
              >
                {suggestedVideos.length === 0 ? (
                  <p style={{ fontSize: "13px", color: COLORS.gray }}>
                    추천 영상이 없습니다.
                  </p>
                ) : (
                  suggestedVideos.map((video, idx) => (
                    <div
                      key={video.id}
                      onClick={() => {
                        if (onVideoClick) {
                          onVideoClick(video);
                        }
                        onClose();
                      }}
                      style={{
                        minWidth: "140px",
                        cursor: "pointer",
                        opacity: phase >= 3 ? 1 : 0,
                        transform:
                          phase >= 3 ? "translateY(0)" : "translateY(15px)",
                        transition: `all 0.3s ease ${0.2 + idx * 0.04}s`,
                      }}
                    >
                      <div
                        style={{
                          width: "140px",
                          height: "180px",
                          backgroundColor: COLORS.lightGray,
                          borderRadius: "8px",
                          marginBottom: "10px",
                          overflow: "hidden",
                          transition:
                            "transform 0.25s ease, box-shadow 0.25s ease",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          background: `linear-gradient(135deg, hsl(${
                            idx * 25 + 200
                          }, 15%, 92%) 0%, hsl(${
                            idx * 25 + 220
                          }, 20%, 88%) 100%)`,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = "scale(1.04)";
                          e.currentTarget.style.boxShadow =
                            "0 8px 20px rgba(0,0,0,0.12)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = "scale(1)";
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      >
                        <svg
                          width="32"
                          height="32"
                          viewBox="0 0 24 24"
                          fill="none"
                        >
                          <polygon points="5,3 19,12 5,21" fill="#ccc" />
                        </svg>
                      </div>
                      <div
                        style={{
                          fontSize: "13px",
                          fontWeight: "600",
                          color: COLORS.dark,
                          marginBottom: "3px",
                          lineHeight: "1.3",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {video.title}
                      </div>
                      <div
                        style={{
                          fontSize: "11px",
                          color: COLORS.gray,
                        }}
                      >
                        {video.tags}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 하단 로고 */}
          <div
            style={{
              padding: "0 32px 20px",
              opacity: phase >= 3 ? 0.5 : 0,
              transition: "opacity 0.3s ease 0.3s",
            }}
          >
            <LogoIcon />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpandableSearch;
