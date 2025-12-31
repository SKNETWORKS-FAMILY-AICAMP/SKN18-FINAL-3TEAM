import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { COLORS } from '../../../constants/theme';

/**
 * Markdown 렌더링 컴포넌트
 * LLM 답변을 Markdown 형식으로 렌더링합니다.
 */
const MarkdownRenderer = ({ content }) => {
  // content가 없거나 빈 문자열인 경우 처리
  if (!content || typeof content !== 'string') {
    return <div style={{ fontSize: '14px', color: COLORS.dark }}>{content || ''}</div>;
  }

  return (
    <div 
      style={{ 
        fontSize: '14px', 
        color: COLORS.dark, 
        lineHeight: '1.6',
        wordWrap: 'break-word',
        overflowWrap: 'break-word',
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // 제목 스타일
        h1: ({ node, ...props }) => (
          <h1
            style={{
              fontSize: '20px',
              fontWeight: '700',
              color: COLORS.dark,
              marginTop: '16px',
              marginBottom: '12px',
              lineHeight: '1.4',
            }}
            {...props}
          />
        ),
        h2: ({ node, ...props }) => (
          <h2
            style={{
              fontSize: '18px',
              fontWeight: '600',
              color: COLORS.dark,
              marginTop: '14px',
              marginBottom: '10px',
              lineHeight: '1.4',
            }}
            {...props}
          />
        ),
        h3: ({ node, ...props }) => (
          <h3
            style={{
              fontSize: '16px',
              fontWeight: '600',
              color: COLORS.dark,
              marginTop: '12px',
              marginBottom: '8px',
              lineHeight: '1.4',
            }}
            {...props}
          />
        ),
        // 단락 스타일
        p: ({ node, ...props }) => (
          <p
            style={{
              fontSize: '14px',
              color: COLORS.dark,
              lineHeight: '1.6',
              marginBottom: '12px',
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
            }}
            {...props}
          />
        ),
        // 강조 (굵게)
        strong: ({ node, ...props }) => (
          <strong
            style={{
              fontWeight: '700',
              color: COLORS.dark,
            }}
            {...props}
          />
        ),
        // 이탤릭
        em: ({ node, ...props }) => (
          <em
            style={{
              fontStyle: 'italic',
              color: COLORS.gray,
            }}
            {...props}
          />
        ),
        // 리스트
        ul: ({ node, ...props }) => (
          <ul
            style={{
              paddingLeft: '20px',
              marginBottom: '12px',
              listStyleType: 'disc',
            }}
            {...props}
          />
        ),
        ol: ({ node, ...props }) => (
          <ol
            style={{
              paddingLeft: '20px',
              marginBottom: '12px',
              listStyleType: 'decimal',
            }}
            {...props}
          />
        ),
        li: ({ node, ...props }) => (
          <li
            style={{
              fontSize: '14px',
              color: COLORS.dark,
              lineHeight: '1.6',
              marginBottom: '6px',
            }}
            {...props}
          />
        ),
        // 코드 블록
        code: ({ node, inline, ...props }) =>
          inline ? (
            <code
              style={{
                backgroundColor: COLORS.lightGray,
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '13px',
                fontFamily: 'monospace',
                color: COLORS.dark,
              }}
              {...props}
            />
          ) : (
            <code
              style={{
                display: 'block',
                backgroundColor: COLORS.lightGray,
                padding: '12px',
                borderRadius: '8px',
                fontSize: '13px',
                fontFamily: 'monospace',
                color: COLORS.dark,
                overflowX: 'auto',
                marginBottom: '12px',
              }}
              {...props}
            />
          ),
        // 인용구
        blockquote: ({ node, ...props }) => (
          <blockquote
            style={{
              borderLeft: `4px solid ${COLORS.primary}`,
              paddingLeft: '16px',
              marginLeft: '0',
              marginBottom: '12px',
              color: COLORS.gray,
              fontStyle: 'italic',
            }}
            {...props}
          />
        ),
        // 링크
        a: ({ node, ...props }) => (
          <a
            style={{
              color: COLORS.primary,
              textDecoration: 'underline',
            }}
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),
        // 구분선
        hr: ({ node, ...props }) => (
          <hr
            style={{
              border: 'none',
              borderTop: `1px solid ${COLORS.lightGray}`,
              margin: '16px 0',
            }}
            {...props}
          />
        ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
