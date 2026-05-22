import React from 'react';

/**
 * Cadence logo — brackets + three-line staff + four checkpoint dots ascending
 * from orange → coral → sage → teal, followed by the "cadence" wordmark.
 *
 * The icon colours are fixed (brand palette). The wordmark colour is the one
 * thing that adapts to context (dark on light, cream on dark).
 */
interface Props {
  height?: number;
  wordmarkColor?: string;          // default: text.primary
  bracketColor?: string;           // default: khaki
  staffColor?: string;             // default: light beige
  showWordmark?: boolean;          // default true; false renders icon only
}

// Source coordinates from the original SVG, viewBox 0 0 680 200, content lives
// in a (40, 60) translated group. We re-emit it in a flat viewBox at native
// dimensions so the `height` prop scales linearly.
const ICON_VIEWBOX = '0 0 230 100';
const FULL_VIEWBOX = '0 0 570 100';

export const Logo: React.FC<Props> = ({
  height = 36,
  wordmarkColor = '#1c1917',
  bracketColor = '#a8a59c',
  staffColor = '#dedcd1',
  showWordmark = true,
}) => {
  const viewBox = showWordmark ? FULL_VIEWBOX : ICON_VIEWBOX;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={viewBox}
      height={height}
      role="img"
      aria-label="Cadence"
    >
      {/* Brackets */}
      <text
        x="0"
        y="78"
        fontFamily='"Inter", system-ui, sans-serif'
        fontSize="78"
        fontWeight="300"
        fill={bracketColor}
      >
        [
      </text>
      {/* Three staff lines */}
      <line x1="36" y1="28" x2="194" y2="28" stroke={staffColor} strokeWidth="1.2" />
      <line x1="36" y1="48" x2="194" y2="48" stroke={staffColor} strokeWidth="1.2" />
      <line x1="36" y1="68" x2="194" y2="68" stroke={staffColor} strokeWidth="1.2" />
      {/* Four checkpoint dots — orange → coral → sage → teal, ascending */}
      <circle cx="60"  cy="68" r="7" fill="#F37726" />
      <circle cx="100" cy="48" r="7" fill="#D17753" />
      <circle cx="140" cy="48" r="7" fill="#7F9081" />
      <circle cx="180" cy="28" r="7" fill="#2BA89E" />
      <text
        x="200"
        y="78"
        fontFamily='"Inter", system-ui, sans-serif'
        fontSize="78"
        fontWeight="300"
        fill={bracketColor}
      >
        ]
      </text>
      {showWordmark && (
        <text
          x="252"
          y="76"
          fontFamily='"Inter", system-ui, sans-serif'
          fontSize="60"
          fontWeight="500"
          letterSpacing="-1.5"
          fill={wordmarkColor}
        >
          cadence
        </text>
      )}
    </svg>
  );
};

export default Logo;
