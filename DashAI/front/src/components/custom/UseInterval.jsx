import { useEffect, useRef } from "react";

const useInterval = (callback, delay) => {
  const callbackRef = useRef(null);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const tick = () => {
      if (callbackRef.current) {
        callbackRef.current();
      }
    };
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
};

export default useInterval;

useInterval.propTypes = {
  callback: PropTypes.func.isRequired,
  delay: PropTypes.number,
};
