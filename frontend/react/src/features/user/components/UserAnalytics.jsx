import { COLORS } from '../../../constants/theme';

const UserAnalytics = () => {
  const chartColors = [COLORS.primary, '#7286ff', '#666', '#999', '#333'];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
        <div
          style={{
            display: 'inline-block',
            padding: '10px 20px',
            backgroundColor: COLORS.gray,
            borderRadius: '8px',
            color: COLORS.white,
            fontSize: '14px',
            fontWeight: '600',
          }}
        >
          기록 분석
        </div>
      </div>
      <div
        style={{
          backgroundColor: COLORS.white,
          borderRadius: '12px',
          border: '1px solid #eee',
          padding: '20px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '30px',
            marginTop: '20px',
          }}
        >
          <svg width="160" height="160" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill={chartColors[0]} />
            <path d="M50 50 L50 10 A40 40 0 0 1 90 50 Z" fill={chartColors[1]} />
            <path d="M50 50 L90 50 A40 40 0 0 1 70 85 Z" fill={chartColors[2]} />
            <path d="M50 50 L70 85 A40 40 0 0 1 30 85 Z" fill={chartColors[3]} />
            <path d="M50 50 L30 85 A40 40 0 0 1 10 50 Z" fill={chartColors[4]} />
          </svg>

          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div
              style={{
                height: '16px',
                borderRadius: '4px',
                width: '100%',
                backgroundColor: chartColors[0],
              }}
            ></div>
            <div
              style={{
                height: '16px',
                borderRadius: '4px',
                width: '75%',
                backgroundColor: chartColors[1],
              }}
            ></div>
            <div
              style={{
                height: '16px',
                borderRadius: '4px',
                width: '50%',
                backgroundColor: chartColors[4],
              }}
            ></div>
            <div
              style={{
                height: '16px',
                borderRadius: '4px',
                width: '30%',
                backgroundColor: chartColors[3],
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserAnalytics;
