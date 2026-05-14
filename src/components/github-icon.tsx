import React from "react";

/**
 * GitHub SVG icon — replaces the removed lucide-react `Github` export.
 * Kept as a drop-in so every `<Github className=... />` still works.
 */
export function Github({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.28-.5-4.72-.5-7 0-2-1.5-3-1.5-3-1.5 0-2 1.72-.28 3.5C4.27 8.02 3.92 9.25 4 10.5c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65S8.93 18.63 9 19v3" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
