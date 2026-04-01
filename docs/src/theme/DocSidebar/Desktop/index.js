import React, { useEffect } from "react";
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

function getSectionFromPath(pathname) {
  if (!pathname) {
    return undefined;
  }

  if (pathname.startsWith("/discover/")) {
    return "discover";
  }

  if (pathname.startsWith("/learn/")) {
    return "learn";
  }

  if (pathname.startsWith("/deep-dive/")) {
    return "deep-dive";
  }

  if (pathname.startsWith("/build/") || pathname.startsWith("/components/")) {
    return "build";
  }

  return undefined;
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

  const section = getSectionFromPath(path);

  useEffect(() => {
    if (typeof document === "undefined") {
      return undefined;
    }

    const root = document.documentElement;
    if (section) {
      root.setAttribute("data-section", section);
    } else {
      root.removeAttribute("data-section");
    }

    return () => {
      if (root.getAttribute("data-section") === section) {
        root.removeAttribute("data-section");
      }
    };
  }, [section]);

  return (
    <div className="dashai-sidebar-desktop" data-section={section}>
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
