import { useId } from "react";

/**
 * The "Volatility Eyes" brand mark - a plain inline SVG (3 shapes, one
 * 2-stop gradient), not an image/icon-font/animation library, so it costs
 * nothing beyond what's already in the DOM. useId keeps the gradient id
 * unique per instance (nav + page hero both render one on the same page).
 */
export function EyeMark({ size = 24 }: { size?: number }) {
  const gradId = useId();
  return (
    <svg
      width={size}
      height={size * 0.625}
      viewBox="0 0 32 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M1 10C4.5 4.5 10 1.5 16 1.5C22 1.5 27.5 4.5 31 10C27.5 15.5 22 18.5 16 18.5C10 18.5 4.5 15.5 1 10Z"
        stroke={`url(#${gradId})`}
        strokeWidth="2"
      />
      <circle cx="16" cy="10" r="5.5" fill={`url(#${gradId})`} />
      <circle cx="14" cy="8" r="1.6" fill="var(--bg)" />
      <defs>
        <linearGradient id={gradId} x1="1" y1="1.5" x2="31" y2="18.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4f8cff" />
          <stop offset="1" stopColor="#8a5cff" />
        </linearGradient>
      </defs>
    </svg>
  );
}
