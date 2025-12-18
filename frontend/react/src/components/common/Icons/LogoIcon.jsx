import { COLORS } from '../../../constants/theme';

const LogoIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="18" cy="18" r="14" fill="#c8e0ff" />
    <path
      d="M28 12 C38 12, 42 20, 42 28 C42 36, 36 42, 28 42 C20 42, 18 38, 18 32"
      fill={COLORS.primary}
      stroke="none"
    />
    <circle cx="28" cy="42" r="5" fill="#333" />
  </svg>
);

export default LogoIcon;
