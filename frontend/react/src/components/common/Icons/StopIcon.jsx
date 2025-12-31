const StopIcon = ({ size = 20, color = '#666', fillColor = '#FFF9E6' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="5" width="14" height="14" fill={fillColor} stroke={color} />
    </svg>
  );
};

export default StopIcon;
