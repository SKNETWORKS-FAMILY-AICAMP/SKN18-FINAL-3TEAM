import api from "./axios";

/**
 * 영상 검색 API (무한 스크롤 지원)
 * @param {string} query - 검색어 (선택, 없으면 인기 영상)
 * @param {string} sort - 정렬 기준 (latest/popular/relevance)
 * @param {number} page - 페이지 번호
 * @param {number} pageSize - 페이지당 개수
 * @param {string[]} tags - 태그 필터 배열
 * @returns {Promise} 검색 결과
 */
export const searchVideos = async (
  query = "",
  sort = "relevance",
  page = 1,
  pageSize = 12,
  tags = []
) => {
  try {
    const params = {
      sort,
      page,
      page_size: pageSize,
    };

    // 검색어가 있을 때만 추가
    if (query && query.trim()) {
      params.q = query.trim();
    }

    // 태그 필터가 있을 때만 추가
    if (tags && tags.length > 0) {
      params.tags = tags.join(",");
    }

    const response = await api.get("/api/search/videos/", { params });
    return response.data;
  } catch (error) {
    console.error("영상 검색 실패:", error);
    throw error;
  }
};
