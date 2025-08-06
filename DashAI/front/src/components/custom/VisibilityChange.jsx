import { useEffect, useState } from "react";

const useVisibilityChange = () => {
  const [isVisible, setIsVisible] = useState < boolean > !document.hidden;

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return isVisible;
};

export default useVisibilityChange;

useVisibilityChange.propTypes = {
  isVisible: PropTypes.bool,
};
