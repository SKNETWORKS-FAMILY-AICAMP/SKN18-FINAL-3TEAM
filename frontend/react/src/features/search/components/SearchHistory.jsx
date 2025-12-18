import { COLORS } from '../../../constants/theme';
import { CloseIcon } from '../../../components/common/Icons';

const SearchHistory = ({ items, onItemClick, onItemDelete, contentVisible }) => {
  return (
    <div style={{ marginBottom: '40px' }}>
      <h3
        style={{
          fontSize: '15px',
          fontWeight: '700',
          color: COLORS.dark,
          marginBottom: '20px',
          letterSpacing: '0.5px',
        }}
      >
        검색 기록
      </h3>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0',
        }}
      >
        {items.map((item, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 0',
              borderBottom: '1px solid #eee',
              cursor: 'pointer',
              opacity: contentVisible ? 1 : 0,
              transform: contentVisible ? 'translateX(0)' : 'translateX(-20px)',
              transition: `all 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${
                0.1 + idx * 0.05
              }s`,
            }}
            onClick={() => onItemClick(item)}
          >
            <span
              style={{
                fontSize: '14px',
                color: COLORS.gray,
              }}
            >
              {item}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onItemDelete(item);
              }}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px',
                opacity: 0.5,
              }}
            >
              <CloseIcon size={14} color="#999" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchHistory;
