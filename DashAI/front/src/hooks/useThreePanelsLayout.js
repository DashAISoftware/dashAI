import { useState, useRef, useEffect, useCallback } from "react";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

const DEFAULT_LAYOUT = {
  leftBarVisible: true,
  rightBarVisible: true,
  leftBarWidth: 20,
  rightBarWidth: 20,
};

const readPersisted = (storageKey) => {
  if (!storageKey) return DEFAULT_LAYOUT;
  try {
    const raw = localStorage.getItem(`layout:${storageKey}`);
    if (!raw) return DEFAULT_LAYOUT;
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_LAYOUT, ...parsed };
  } catch {
    return DEFAULT_LAYOUT;
  }
};

export function useThreePanelLayout({
  storageKey,
  overlayRightOnCompact = false,
  compactBreakpoint = "md",
} = {}) {
  const initial = readPersisted(storageKey);
  const [leftBarVisible, setLeftBarVisible] = useState(initial.leftBarVisible);
  const [rightBarVisible, setRightBarVisible] = useState(
    initial.rightBarVisible,
  );
  const [leftBarWidth, setLeftBarWidth] = useState(initial.leftBarWidth);
  const [rightBarWidth, setRightBarWidth] = useState(initial.rightBarWidth);

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(
        `layout:${storageKey}`,
        JSON.stringify({
          leftBarVisible,
          rightBarVisible,
          leftBarWidth,
          rightBarWidth,
        }),
      );
    } catch {
      // ignore quota / disabled storage
    }
  }, [
    storageKey,
    leftBarVisible,
    rightBarVisible,
    leftBarWidth,
    rightBarWidth,
  ]);

  const [isTogglingLeft, setIsTogglingLeft] = useState(false);
  const [isTogglingRight, setIsTogglingRight] = useState(false);

  const isResizingLeft = useRef(false);
  const isResizingRight = useRef(false);

  const handleMouseMove = useCallback((e) => {
    const container = document.querySelector('[data-container="datasets"]');
    if (!container) return;

    const rect = container.getBoundingClientRect();

    if (isResizingLeft.current) {
      const w = ((e.clientX - rect.left) / rect.width) * 100;
      if (w >= 15 && w <= 40) setLeftBarWidth(w);
    }

    if (isResizingRight.current) {
      const w = ((rect.right - e.clientX) / rect.width) * 100;
      if (w >= 15 && w <= 40) setRightBarWidth(w);
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizingLeft.current = false;
    isResizingRight.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleToggleLeft = useCallback(() => {
    setIsTogglingLeft(true);
    setLeftBarVisible((v) => !v);

    setTimeout(() => {
      setIsTogglingLeft(false);
    }, 300);
  }, []);

  const handleToggleRight = useCallback(() => {
    setIsTogglingRight(true);
    setRightBarVisible((v) => !v);

    setTimeout(() => {
      setIsTogglingRight(false);
    }, 300);
  }, []);

  const theme = useTheme();
  const isCompact = useMediaQuery(theme.breakpoints.down(compactBreakpoint));
  const isRightOverlayActive = overlayRightOnCompact && isCompact;
  const effectiveRightVisible = isRightOverlayActive ? false : rightBarVisible;
  const effectiveRightWidth = isRightOverlayActive ? 0 : rightBarWidth;

  const centerWidth =
    leftBarVisible && effectiveRightVisible
      ? 100 - leftBarWidth - effectiveRightWidth
      : leftBarVisible
        ? 100 - leftBarWidth
        : effectiveRightVisible
          ? 100 - effectiveRightWidth
          : 100;

  return {
    leftBarVisible,
    rightBarVisible,
    leftBarWidth,
    rightBarWidth,
    centerWidth,
    isCompact,
    isRightOverlayActive,

    handleToggleLeft,
    handleToggleRight,

    isTogglingLeft,
    isTogglingRight,

    bindLeftResize: {
      onMouseDown: () => {
        isResizingLeft.current = true;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      },
    },

    bindRightResize: {
      onMouseDown: () => {
        isResizingRight.current = true;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      },
    },
  };
}
