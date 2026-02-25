import { useState, useRef, useEffect, useCallback } from "react";

export function useThreePanelLayout() {
  const [leftBarVisible, setLeftBarVisible] = useState(true);
  const [rightBarVisible, setRightBarVisible] = useState(true);
  const [leftBarWidth, setLeftBarWidth] = useState(20);
  const [rightBarWidth, setRightBarWidth] = useState(20);

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

  const centerWidth =
    leftBarVisible && rightBarVisible
      ? 100 - leftBarWidth - rightBarWidth
      : leftBarVisible
        ? 100 - leftBarWidth
        : rightBarVisible
          ? 100 - rightBarWidth
          : 100;

  return {
    leftBarVisible,
    rightBarVisible,
    leftBarWidth,
    rightBarWidth,
    centerWidth,

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
