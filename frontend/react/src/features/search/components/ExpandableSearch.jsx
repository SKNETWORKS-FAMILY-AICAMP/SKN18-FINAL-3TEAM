import { useState, useEffect, useRef } from "react";
import { COLORS } from "../../../constants/theme";
import {
  SearchIcon,
  CloseIcon,
  LogoIcon,
  TagIcon,
} from "../../../components/common/Icons";
import {
  getSearchHistory,
  createSearchHistory,
  getRecommendedKeyword,
  getRecommendedVideos,
} from "../../../api/activityApi";
import { getPopularVideos } from "../../../api/videoApi";
import { searchVideos } from "../../../api/searchApi";
import { getThumbnailUrl } from "../../../utils/imageUtils";

const ExpandableSearch = ({
  isOpen,
  onClose,
  isLoggedIn = false,
  onSearch,
  onVideoClick,
}) => {
  const [searchValue, setSearchValue] = useState("");
  const [phase, setPhase] = useState(0); // 0: closed, 1: expanding width, 2: expanding height, 3: content visible
  const [hasBeenOpened, setHasBeenOpened] = useState(false); // 한 번이라도 열렸는지 추적
  const [shouldRender, setShouldRender] = useState(false); // 실제로 렌더링할지 여부
  const inputRef = useRef(null);
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollTimerRef = useRef(null);

  // API에서 가져온 데이터
  const [searchHistory, setSearchHistory] = useState([]); // {id, search_query} 객체 배열
  const [hiddenHistoryIds, setHiddenHistoryIds] = useState(() => {
    // localStorage에서 숨긴 검색 기록 ID 목록 가져오기
    const stored = localStorage.getItem("hiddenSearchHistory");
    return stored ? JSON.parse(stored) : [];
  });
  const [recommendedTags, setRecommendedTags] = useState([]); // 태그 (아이콘으로 표시)
  const [recommendedKeywords, setRecommendedKeywords] = useState([]); // 키워드 (#으로 표시)
  const [suggestedVideos, setSuggestedVideos] = useState([]);
  const [isSearching, setIsSearching] = useState(false); // 검색 중 상태

  // API에서 데이터 로드 (모달이 열릴 때마다 최신 데이터 가져오기)
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 로그인한 경우 추천 태그/키워드 로드
        if (isLoggedIn) {
          try {
            const recommendedResponse = await getRecommendedKeyword();
            console.log("추천 키워드 API 응답:", recommendedResponse);
            if (recommendedResponse?.data) {
              // 태그는 아이콘으로 표시할 배열
              setRecommendedTags(recommendedResponse.data.tag || []);
              // 키워드는 #으로 표시할 배열 (video_keyword + recommended_keyword 합치기)
              const allKeywords = [
                ...(recommendedResponse.data.video_keyword || []),
                ...(recommendedResponse.data.recommended_keyword || []),
              ];
              console.log("설정된 추천 키워드:", allKeywords);
              setRecommendedKeywords(allKeywords);
            }
          } catch (error) {
            console.error("추천 키워드 로드 실패:", error);
            setRecommendedTags([]);
            setRecommendedKeywords([]);
          }

          // 검색 기록 로드
          const historyResponse = await getSearchHistory();
          if (historyResponse?.data) {
            // {id, search_query} 형태로 저장
            setSearchHistory(
              historyResponse.data.map((h) => ({
                id: h.id,
                search_query: h.search_query,
              }))
            );
          }
        }

        // 검색어가 없을 때는 인기 영상 로드
        if (!searchValue.trim()) {
          const videosResponse = await getPopularVideos();
          if (videosResponse?.data) {
            setSuggestedVideos(
              videosResponse.data.map((v) => ({
                id: v.id,
                title: v.title,
                tags: v.tags || [],
                thumbnail_url: v.thumbnail_url || null,
              }))
            );
          }
        }
      } catch (error) {
        console.error("검색 데이터 로드 실패:", error);
      }
    };

    // 모달이 열릴 때마다 최신 데이터 가져오기
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, isLoggedIn, searchValue]);

  // 검색어 입력 시 실시간 검색 (디바운싱 적용)
  useEffect(() => {
    if (!isOpen) return;

    const searchQuery = searchValue.trim();

    // 검색어가 없으면 인기 영상 로드
    if (!searchQuery) {
      const fetchPopular = async () => {
        try {
          const videosResponse = await getPopularVideos();
          if (videosResponse?.data) {
            setSuggestedVideos(
              videosResponse.data.map((v) => ({
                id: v.id,
                title: v.title,
                tags: v.tags || [],
                thumbnail_url: v.thumbnail_url || null,
              }))
            );
          }
        } catch (error) {
          console.error("인기 영상 로드 실패:", error);
        }
      };
      fetchPopular();
      return;
    }

    // 검색어가 있을 때는 디바운싱 적용
    // 실시간 검색에서는 검색 기록을 저장하지 않음 (saveHistory=false)
    setIsSearching(true);
    const debounceTimer = setTimeout(async () => {
      try {
        const response = await searchVideos(
          searchQuery,
          "relevance",
          1,
          12,
          [],
          false
        );
        if (response?.data?.results) {
          setSuggestedVideos(
            response.data.results.map((v) => ({
              id: v.id,
              title: v.title,
              tags: v.tags || [],
              thumbnail_url: v.thumbnail_url || null,
            }))
          );
        }
      } catch (error) {
        console.error("검색 실패:", error);
        setSuggestedVideos([]);
      } finally {
        setIsSearching(false);
      }
    }, 300); // 300ms 디바운싱

    return () => {
      clearTimeout(debounceTimer);
    };
  }, [searchValue, isOpen]);

  // 검색 실행 시 검색 기록 저장 및 검색 페이지로 이동
  // 로그인 여부와 관계없이 항상 검색 결과 페이지로 이동
  const handleSearch = async () => {
    if (!searchValue.trim()) return;

    const searchQuery = searchValue.trim();

    // 검색 기록 저장 (로그인한 경우만, 실패해도 계속 진행)
    if (isLoggedIn) {
      try {
        const response = await createSearchHistory(searchQuery);
        // 검색 기록 업데이트 (최대 10개)
        if (response?.data) {
          const newHistory = {
            id: response.data.id,
            search_query: searchQuery,
          };
          setSearchHistory((prev) =>
            [
              newHistory,
              ...prev.filter((h) => h.search_query !== searchQuery),
            ].slice(0, 10)
          );
        }
      } catch (error) {
        console.error("검색 기록 저장 실패:", error);
        // 검색 기록 저장 실패해도 검색은 계속 진행
      }
    }

    // 검색 페이지로 이동 (로그인 여부와 관계없이 항상 실행)
    // 로그인하지 않은 사용자도 검색 결과를 볼 수 있도록 보장
    if (onSearch) {
      onSearch(searchQuery);
    } else {
      console.warn("onSearch 콜백이 제공되지 않았습니다.");
    }

    // 입력창 초기화 및 검색창 닫기
    setSearchValue("");
    onClose();
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
    setSearchValue(""); // 검색창 닫을 때 입력값 초기화
    onClose();
  };

  // 검색 기록 삭제 (UI에서만 숨김, DB는 유지)
  const handleDeleteHistory = (historyId) => {
    const updatedHiddenIds = [...hiddenHistoryIds, historyId];
    setHiddenHistoryIds(updatedHiddenIds);
    // localStorage에 저장
    localStorage.setItem(
      "hiddenSearchHistory",
      JSON.stringify(updatedHiddenIds)
    );
  };

  // 숨기지 않은 검색 기록만 필터링
  const visibleSearchHistory = searchHistory.filter(
    (h) => !hiddenHistoryIds.includes(h.id)
  );

  // 스크롤 이벤트 핸들러
  const handleScroll = () => {
    setIsScrolling(true);

    // 기존 타이머 제거
    if (scrollTimerRef.current) {
      clearTimeout(scrollTimerRef.current);
    }

    // 1초 후 스크롤바 숨김
    scrollTimerRef.current = setTimeout(() => {
      setIsScrolling(false);
    }, 1000);
  };

  // 초기 로드 시에는 렌더링하지 않음
  if (!shouldRender) return null;

  return (
    <>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: ${
            isScrolling ? "rgba(0, 0, 0, 0.2)" : "transparent"
          };
          border-radius: 3px;
          transition: background-color 0.3s ease;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background-color: rgba(0, 0, 0, 0.3);
        }

        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: ${
            isScrolling ? "rgba(0, 0, 0, 0.2)" : "transparent"
          } transparent;
        }
      `}</style>
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
                  color: COLORS.textPrimary,
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
                        color: COLORS.textPrimary,
                        marginBottom: "16px",
                      }}
                    >
                      검색 기록
                    </h3>

                    <div
                      onScroll={handleScroll}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        maxHeight: "135px",
                        overflowY: "auto",
                        paddingRight: "8px",
                      }}
                      className="custom-scrollbar"
                    >
                      {visibleSearchHistory.length === 0 ? (
                        <p style={{ fontSize: "13px", color: COLORS.gray }}>
                          검색 기록이 없습니다.
                        </p>
                      ) : (
                        visibleSearchHistory.map((item, idx) => (
                          <div
                            key={item.id}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "10px 0",
                              borderBottom: "1px solid #f0f0f0",
                              opacity: phase >= 3 ? 1 : 0,
                              transform:
                                phase >= 3
                                  ? "translateX(0)"
                                  : "translateX(-15px)",
                              transition: `all 0.3s ease ${0.15 + idx * 0.05}s`,
                            }}
                          >
                            <span
                              style={{
                                fontSize: "13px",
                                color: COLORS.gray,
                                cursor: "pointer",
                                flex: 1,
                              }}
                              onClick={() => {
                                setSearchValue(item.search_query);
                                if (onSearch) {
                                  onSearch(item.search_query);
                                }
                                setSearchValue("");
                                onClose();
                              }}
                            >
                              {item.search_query}
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
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteHistory(item.id);
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

                  {/* 추천 태그 */}
                  <div>
                    <h3
                      style={{
                        fontSize: "14px",
                        fontWeight: "700",
                        color: COLORS.dark,
                        marginBottom: "16px",
                      }}
                    >
                      추천 태그
                    </h3>

                    <div
                      onScroll={handleScroll}
                      className="custom-scrollbar"
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                        maxHeight: "200px",
                        overflowY: "auto",
                        paddingRight: "8px",
                      }}
                    >
                      {recommendedTags.length === 0 &&
                      recommendedKeywords.length === 0 ? (
                        <p style={{ fontSize: "13px", color: COLORS.gray }}>
                          추천 태그가 없습니다.
                        </p>
                      ) : (
                        <>
                          {/* 키워드 (#으로 표시) - 항상 앞쪽 */}
                          {recommendedKeywords.map((keyword, idx) => (
                            <button
                              key={`keyword-${idx}`}
                              onClick={() => {
                                // 검색기록에 저장하지 않고 바로 검색 페이지로 이동
                                if (onSearch) {
                                  onSearch(keyword);
                                }
                                onClose();
                              }}
                              style={{
                                padding: "8px 16px",
                                backgroundColor: COLORS.jadePale, // 밝은 제이드
                                border: `1.5px solid ${COLORS.jadePale}`,
                                borderRadius: "20px",
                                color: COLORS.dark, // 블랙
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                                transition: "all 0.2s ease",
                                opacity: phase >= 3 ? 1 : 0,
                                transform:
                                  phase >= 3
                                    ? "translateY(0)"
                                    : "translateY(8px)",
                                transitionDelay: `${0.2 + idx * 0.025}s`,
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor =
                                  COLORS.jadeLight; // 제이드 라이트
                                e.currentTarget.style.borderColor = COLORS.jadeLight;
                                e.currentTarget.style.color = COLORS.dark; // 블랙 유지
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor =
                                  COLORS.jadePale; // 밝은 제이드
                                e.currentTarget.style.borderColor =
                                  COLORS.jadePale;
                                e.currentTarget.style.color = COLORS.dark; // 블랙
                              }}
                            >
                              #{keyword}
                            </button>
                          ))}
                          {/* 태그 (아이콘 옆에 텍스트) - 항상 뒤쪽 */}
                          {recommendedTags.map((tag, idx) => (
                            <button
                              key={`tag-${idx}`}
                              onClick={() => {
                                // 검색기록에 저장하지 않고 바로 검색 페이지로 이동
                                if (onSearch) {
                                  onSearch(tag);
                                }
                                onClose();
                              }}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                                padding: "8px 16px",
                                backgroundColor: COLORS.sub_color, // 연노랑색
                                border: `1.5px solid ${COLORS.sub_color}`,
                                borderRadius: "20px",
                                color: COLORS.dark, // 블랙
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                                transition: "all 0.2s ease",
                                opacity: phase >= 3 ? 1 : 0,
                                transform:
                                  phase >= 3
                                    ? "translateY(0)"
                                    : "translateY(8px)",
                                transitionDelay: `${
                                  0.2 +
                                  (recommendedKeywords.length + idx) * 0.025
                                }s`,
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor =
                                  COLORS.sky; // 하늘색
                                e.currentTarget.style.borderColor = COLORS.sky;
                                e.currentTarget.style.color = COLORS.dark; // 블랙 유지
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor =
                                  COLORS.sub_color; // 연노랑색
                                e.currentTarget.style.borderColor =
                                  COLORS.sub_color;
                                e.currentTarget.style.color = COLORS.dark; // 블랙
                              }}
                            >
                              <TagIcon size={14} color="currentColor" />
                              <span>{tag}</span>
                            </button>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* 우측: 영상 표시 */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <h3
                  style={{
                    fontSize: "14px",
                    fontWeight: "700",
                    color: COLORS.textPrimary,
                    marginBottom: "16px",
                  }}
                >
                  {searchValue
                    ? `"${searchValue}" 관련 영상`
                    : isLoggedIn
                    ? "인기 영상"
                    : ""}
                </h3>

                {/* 로그인: 항상 영상 표시, 비회원: 검색시에만 표시 */}
                {(isLoggedIn || searchValue) && (
                  <div
                    style={{
                      display: "flex",
                      gap: "16px",
                      overflowX: "auto",
                      paddingBottom: "8px",
                    }}
                  >
                    {isSearching ? (
                      <p style={{ fontSize: "13px", color: COLORS.gray }}>
                        검색 중...
                      </p>
                    ) : suggestedVideos.length === 0 ? (
                      <p style={{ fontSize: "13px", color: COLORS.gray }}>
                        {searchValue
                          ? "검색 결과가 없습니다."
                          : isLoggedIn
                          ? "인기 영상이 없습니다."
                          : ""}
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
                              borderRadius: "8px",
                              marginBottom: "10px",
                              overflow: "hidden",
                              transition:
                                "transform 0.25s ease, box-shadow 0.25s ease",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              ...(video.thumbnail_url
                                ? {
                                    backgroundImage: `url(${getThumbnailUrl(
                                      video.thumbnail_url
                                    )})`,
                                    backgroundSize: "cover",
                                    backgroundPosition: "center",
                                  }
                                : {
                                    background: `linear-gradient(135deg, hsl(${
                                      idx * 25 + 200
                                    }, 15%, 92%) 0%, hsl(${
                                      idx * 25 + 220
                                    }, 20%, 88%) 100%)`,
                                  }),
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
                            {!video.thumbnail_url && (
                              <svg
                                width="32"
                                height="32"
                                viewBox="0 0 24 24"
                                fill="none"
                              >
                                <polygon points="5,3 19,12 5,21" fill="#ccc" />
                              </svg>
                            )}
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
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              flexWrap: "wrap",
                            }}
                          >
                            {video.tags && video.tags.length > 0
                              ? video.tags.map((tag, tagIdx) => (
                                  <span
                                    key={tagIdx}
                                    style={{
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: "3px",
                                    }}
                                  >
                                    <TagIcon size={10} color={COLORS.gray} />
                                    <span>{tag}</span>
                                  </span>
                                ))
                              : null}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
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
    </>
  );
};

export default ExpandableSearch;
