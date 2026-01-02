import React, { useState, useEffect, useRef, useCallback } from "react";
import VideoGrid from "../features/video/components/VideoGrid";
import { searchVideos } from "../api/searchApi";
import { COLORS } from "../constants/theme";

const SearchResultPage = ({ query, onVideoClick, isLoggedIn }) => {
  const [videos, setVideos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState("relevance");
  const [selectedTags, setSelectedTags] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);

  // 무한 스크롤 상태
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const observerTarget = useRef(null);

  // 검색 결과 초기화 및 로드
  useEffect(() => {
    const fetchSearchResults = async () => {
      setIsLoading(true);
      setError(null);
      setPage(1);
      setVideos([]);
      setHasMore(true);

      try {
        const response = await searchVideos(query, sortBy, 1, 12, selectedTags);

        const formattedVideos = response.data.results.map((video) => ({
          id: video.id,
          title: video.title,
          tags: video.tags || [],
          likes_count: video.likes_count,
          comments_count: video.comments_count,
          thumbnail_url: video.thumbnail_url,
        }));

        setVideos(formattedVideos);
        setHasMore(response.data.pagination.has_next);

        // 사용 가능한 태그 추출
        const allTags = response.data.results.flatMap((v) => v.tags || []);
        const uniqueTags = [...new Set(allTags)];
        setAvailableTags(uniqueTags);
      } catch (err) {
        console.error("검색 실패:", err);
        setError("검색 중 오류가 발생했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSearchResults();
  }, [query, sortBy, selectedTags]);

  // 무한 스크롤: 다음 페이지 로드
  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);

    try {
      const nextPage = page + 1;
      const response = await searchVideos(
        query,
        sortBy,
        nextPage,
        12,
        selectedTags
      );

      const formattedVideos = response.data.results.map((video) => ({
        id: video.id,
        title: video.title,
        tags: video.tags || [],
        likes_count: video.likes_count,
        comments_count: video.comments_count,
        thumbnail_url: video.thumbnail_url,
      }));

      setVideos((prev) => [...prev, ...formattedVideos]);
      setPage(nextPage);
      setHasMore(response.data.pagination.has_next);
    } catch (err) {
      console.error("추가 로드 실패:", err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [page, hasMore, isLoadingMore, query, sortBy, selectedTags]);

  // Intersection Observer 설정 (무한 스크롤)
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [loadMore, hasMore, isLoadingMore]);

  // 태그 토글
  const toggleTag = (tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  // 태그 전체 해제
  const clearTags = () => {
    setSelectedTags([]);
  };

  return (
    <div
      style={{
        padding: "100px 70px 70px",
        minHeight: "100vh",
        backgroundColor: COLORS.background,
      }}
    >
      {/* 검색 헤더 */}
      <div style={{ marginBottom: "30px" }}>
        {query ? (
          <h1 style={{ color: COLORS.textPrimary, marginBottom: "16px" }}>
            '{query}' 검색 결과
          </h1>
        ) : (
          <h1 style={{ color: COLORS.textPrimary, marginBottom: "16px" }}>
            인기 영상
          </h1>
        )}

        {/* 정렬 옵션 */}
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <button
            onClick={() => setSortBy("relevance")}
            style={{
              padding: "8px 16px",
              backgroundColor:
                sortBy === "relevance" ? COLORS.accent : "transparent",
              color: COLORS.textPrimary,
              border: `1px solid ${COLORS.accent}`,
              borderRadius: "8px",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            관련도순
          </button>
          <button
            onClick={() => setSortBy("latest")}
            style={{
              padding: "8px 16px",
              backgroundColor:
                sortBy === "latest" ? COLORS.accent : "transparent",
              color: COLORS.textPrimary,
              border: `1px solid ${COLORS.accent}`,
              borderRadius: "8px",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            최신순
          </button>
          <button
            onClick={() => setSortBy("popular")}
            style={{
              padding: "8px 16px",
              backgroundColor:
                sortBy === "popular" ? COLORS.accent : "transparent",
              color: COLORS.textPrimary,
              border: `1px solid ${COLORS.accent}`,
              borderRadius: "8px",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            인기순
          </button>
        </div>

        {/* 태그 필터 */}
        {availableTags.length > 0 && (
          <div style={{ marginBottom: "20px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "10px",
              }}
            >
              <span style={{ color: COLORS.textSecondary, fontSize: "14px" }}>
                태그 필터:
              </span>
              {selectedTags.length > 0 && (
                <button
                  onClick={clearTags}
                  style={{
                    padding: "4px 12px",
                    backgroundColor: "transparent",
                    color: COLORS.accent,
                    border: `1px solid ${COLORS.accent}`,
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  전체 해제
                </button>
              )}
            </div>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              {availableTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  style={{
                    padding: "6px 12px",
                    backgroundColor: selectedTags.includes(tag)
                      ? COLORS.accent
                      : "rgba(255, 255, 255, 0.1)",
                    color: COLORS.textPrimary,
                    border: `1px solid ${
                      selectedTags.includes(tag)
                        ? COLORS.accent
                        : "rgba(255, 255, 255, 0.2)"
                    }`,
                    borderRadius: "16px",
                    cursor: "pointer",
                    fontSize: "13px",
                    transition: "all 0.2s",
                  }}
                >
                  #{tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 로딩 상태 */}
      {isLoading && (
        <div
          style={{
            color: COLORS.textSecondary,
            textAlign: "center",
            padding: "50px",
          }}
        >
          검색 중...
        </div>
      )}

      {/* 에러 상태 */}
      {error && (
        <div
          style={{ color: "red", textAlign: "center", padding: "50px" }}
        >
          {error}
        </div>
      )}

      {/* 검색 결과 없음 */}
      {!isLoading && !error && videos.length === 0 && (
        <div
          style={{
            color: COLORS.textSecondary,
            textAlign: "center",
            padding: "50px",
          }}
        >
          {query ? "검색 결과가 없습니다." : "영상이 없습니다."}
        </div>
      )}

      {/* 검색 결과 */}
      {!isLoading && !error && videos.length > 0 && (
        <>
          <p style={{ color: COLORS.textSecondary, marginBottom: "20px" }}>
            {videos.length}개의 영상
            {hasMore && " (스크롤하여 더보기)"}
          </p>
          <VideoGrid videos={videos} onVideoClick={onVideoClick} />

          {/* 무한 스크롤 트리거 */}
          <div
            ref={observerTarget}
            style={{ height: "20px", margin: "20px 0" }}
          />

          {/* 추가 로딩 표시 */}
          {isLoadingMore && (
            <div
              style={{
                color: COLORS.textSecondary,
                textAlign: "center",
                padding: "20px",
              }}
            >
              로딩 중...
            </div>
          )}

          {/* 더 이상 결과 없음 */}
          {!hasMore && videos.length > 0 && (
            <div
              style={{
                color: COLORS.textSecondary,
                textAlign: "center",
                padding: "20px",
              }}
            >
              모든 검색 결과를 불러왔습니다.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SearchResultPage;
