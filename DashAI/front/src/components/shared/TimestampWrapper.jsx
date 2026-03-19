import React from "react";
import { useTimestamp } from "../../hooks/useTimestamp";

const TimestampWrapper = ({ children, eventName }) => {
  const { handleClick } = useTimestamp({ eventName });

  if (!children) {
    return null;
  }

  if (!eventName) {
    return children;
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick(e);
      }}
    >
      {children}
    </div>
  );
};

export default TimestampWrapper;
