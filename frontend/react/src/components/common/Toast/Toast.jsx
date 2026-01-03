import { useEffect } from 'react';
import { COLORS } from '../../../constants/theme';
import { CloseIcon, CheckIcon } from '../Icons';

const Toast = ({ message, type = 'success', duration = 3000, onClose }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const bgColor = type === 'success' ? COLORS.primary : type === 'error' ? '#ff4444' : '#666';
  const Icon = type === 'success' ? CheckIcon : CloseIcon;

  return (
    <div
      style={{
        position: 'fixed',
        top: '80px',
        right: '20px',
        backgroundColor: bgColor,
        color: type === 'success' ? COLORS.dark : '#fff',
        padding: '16px 20px',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        minWidth: '300px',
        maxWidth: '400px',
        zIndex: 10000,
        animation: 'slideInRight 0.3s ease-out',
      }}
    >
      <Icon size={20} color={type === 'success' ? COLORS.dark : '#fff'} />
      <span style={{ flex: 1, fontSize: '14px', fontWeight: '500' }}>
        {message}
      </span>
      <button
        onClick={onClose}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '4px',
          display: 'flex',
          alignItems: 'center',
          opacity: 0.7,
          transition: 'opacity 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
        onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
      >
        <CloseIcon size={16} color={type === 'success' ? COLORS.dark : '#fff'} />
      </button>

      <style>
        {`
          @keyframes slideInRight {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
        `}
      </style>
    </div>
  );
};

export default Toast;
