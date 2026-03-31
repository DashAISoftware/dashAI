import React from "react";
import clsx from "clsx";
import { useThemeConfig } from "@docusaurus/theme-common";
import Content from "@theme/DocSidebar/Desktop/Content";

function HamburgerIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

export default function DocSidebarDesktop({
  path,
  sidebar,
  onCollapse,
  isHidden,
}) {
  const {
    docs: {
      sidebar: { hideable },
    },
  } = useThemeConfig();

  if (isHidden) {
    return null;
  }

  return (
    <div className="dashai-sidebar-desktop">
      {/* Navbar-height header row — matches the top bar visually */}
      {hideable && (
        <div className="dashai-sidebar-header-row">
          <button
            type="button"
            className="dashai-sidebar-toggle-btn"
            onClick={onCollapse}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <HamburgerIcon />
          </button>
        </div>
      )}
      <Content path={path} sidebar={sidebar} />
    </div>
  );
}
