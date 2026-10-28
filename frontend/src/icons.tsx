// Inline SVG icon set — hand-drawn 24-grid stroke icons, 1.5px stroke,
// rendered at 20px by default. No icon fonts.
import React from "react";

export type IconProps = React.SVGProps<SVGSVGElement> & { size?: number };

export function SvgIcon({ size = 20, children, ...rest }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconGrid = (p: IconProps) => (
  <SvgIcon {...p}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
  </SvgIcon>
);

export const IconUsers = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="9" cy="7" r="3.5" />
    <path d="M2.5 21v-1.5a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5V21" />
    <path d="M16 3.8a3.5 3.5 0 0 1 0 6.4" />
    <path d="M20.5 20.2v-1a5 5 0 0 0-3.5-4.78" />
  </SvgIcon>
);

export const IconUserPlus = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="9" cy="7" r="3.5" />
    <path d="M2.5 21v-1.5a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5V21" />
    <path d="M18.5 8v5" />
    <path d="M21 10.5h-5" />
  </SvgIcon>
);

export const IconUser = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="12" cy="7.5" r="3.75" />
    <path d="M4.5 21v-.75A5.25 5.25 0 0 1 9.75 15h4.5a5.25 5.25 0 0 1 5.25 5.25v.75" />
  </SvgIcon>
);

export const IconCalendar = (p: IconProps) => (
  <SvgIcon {...p}>
    <rect x="3.5" y="4.5" width="17" height="16" rx="2" />
    <path d="M8 2.5v4" />
    <path d="M16 2.5v4" />
    <path d="M3.5 10h17" />
  </SvgIcon>
);

export const IconBook = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
  </SvgIcon>
);

export const IconBanknote = (p: IconProps) => (
  <SvgIcon {...p}>
    <rect x="2.5" y="6" width="19" height="12" rx="2" />
    <circle cx="12" cy="12" r="2.75" />
    <path d="M6 12h.01" />
    <path d="M18 12h.01" />
  </SvgIcon>
);

export const IconFile = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M14 2.5H6.5a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8z" />
    <path d="M14 2.5V8h5.5" />
    <path d="M8.5 13h7" />
    <path d="M8.5 16.5h4.5" />
  </SvgIcon>
);

export const IconSparkles = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18.2l-1.8-5.6L4.7 10.8 10.2 9z" />
    <path d="M18.5 16.5v4" />
    <path d="M20.5 18.5h-4" />
  </SvgIcon>
);

export const IconPen = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M11.5 4.5H5a2 2 0 0 0-2 2v12.5a2 2 0 0 0 2 2h12.5a2 2 0 0 0 2-2V12" />
    <path d="M18.4 2.6a2 2 0 0 1 2.8 2.8L13 13.6l-3.6 1 1-3.6z" />
  </SvgIcon>
);

export const IconLogout = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M9 21H5.5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2H9" />
    <path d="M16 17l5-5-5-5" />
    <path d="M21 12H9" />
  </SvgIcon>
);

export const IconSearch = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20.5 20.5 16.3 16.3" />
  </SvgIcon>
);

export const IconAlert = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M10.3 4.1 2.3 17.6a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.4 0z" />
    <path d="M12 9.5V13" />
    <path d="M12 16.8h.01" />
  </SvgIcon>
);

export const IconCheck = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M20 6.5 9.5 17 4 11.5" />
  </SvgIcon>
);

export const IconX = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M17.5 6.5 6.5 17.5" />
    <path d="M6.5 6.5l11 11" />
  </SvgIcon>
);

export const IconChevronDown = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M6 9.5l6 6 6-6" />
  </SvgIcon>
);

export const IconTrendUp = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M22 7l-8.5 8.5-5-5L2 17" />
    <path d="M16 7h6v6" />
  </SvgIcon>
);

export const IconTrendDown = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M22 17l-8.5-8.5-5 5L2 7" />
    <path d="M16 17h6v-6" />
  </SvgIcon>
);

export const IconTarget = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="12" cy="12" r="8.75" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none" />
  </SvgIcon>
);

export const IconAward = (p: IconProps) => (
  <SvgIcon {...p}>
    <circle cx="12" cy="9" r="5.5" />
    <path d="M8.7 13.8 7.2 21.2l4.8-2.4 4.8 2.4-1.5-7.4" />
  </SvgIcon>
);

export const IconRupee = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M6.5 3.5h11" />
    <path d="M6.5 8h11" />
    <path d="M10 3.5c2.8 0 4.5 1.6 4.5 4.5S12.8 12.5 10 12.5H6.5L14.5 20.5" />
  </SvgIcon>
);

export const IconShield = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M12 2.5 4.5 5.5v5.2c0 4.6 3.2 8 7.5 9.8 4.3-1.8 7.5-5.2 7.5-9.8V5.5z" />
    <path d="M9 11.8l2.2 2.2L15.5 9.5" />
  </SvgIcon>
);

export const IconSend = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M20.5 2.5 10 13" />
    <path d="M20.5 2.5 14 20.5l-4-7.5-7.5-4z" />
  </SvgIcon>
);

export const IconRefresh = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M20.5 5.5v5h-5" />
    <path d="M3.5 18.5v-5h5" />
    <path d="M18.8 10.4a6.5 6.5 0 0 0-10.6-4.1L3.5 10.5" />
    <path d="M5.2 13.6a6.5 6.5 0 0 0 10.6 4.1l4.7-4.2" />
  </SvgIcon>
);

export const IconGradCap = (p: IconProps) => (
  <SvgIcon {...p}>
    <path d="M12 4 2.5 8.75 12 13.5l9.5-4.75z" />
    <path d="M6 11.5v4.4c0 1.6 2.7 3.1 6 3.1s6-1.5 6-3.1v-4.4" />
    <path d="M21.5 9.5v4.5" />
  </SvgIcon>
);
