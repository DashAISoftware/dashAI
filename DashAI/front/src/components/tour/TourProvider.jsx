import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import Joyride from "react-joyride";
import { useTranslation } from "react-i18next";
import { useTour } from "../../hooks/useTour";
import { tours } from "../../constants/tours";
import { tourStyles } from "./tourStyles";
import { CustomTooltip } from "./CustomTooltip";
import { useTourRegistry } from "../../contexts/TourRegistryContext";

const TourContext = createContext(null);
export const useTourContext = () => useContext(TourContext);

export const TourProvider = ({
  tourKey,
  children,
  disabled: disabledProp = false,
  disabledMessage: disabledMessageProp = "Tour not available",
}) => {
  const { t } = useTranslation(["common"]);
  const registry = useTourRegistry();
  const regIdRef = useRef(null);

  const {
    run,
    stepIndex,
    startTour,
    stopTour,
    resetTour,
    resetAllTours,
    handleJoyrideCallback,
    goToStep,
    nextStep,
  } = useTour(tourKey);

  const tourData = tours[tourKey];

  const [disabled, setDisabledState] = useState(disabledProp);
  const [disabledMessage, setDisabledMessageState] = useState(disabledMessageProp);

  // Exposed via context so child components can update the navbar button's disabled state
  const setDisabled = useCallback((d, msg) => {
    setDisabledState(d);
    if (msg !== undefined) setDisabledMessageState(msg);
  }, []);

  // Sync if disabled/disabledMessage props change from parent
  useEffect(() => {
    setDisabledState(disabledProp);
    setDisabledMessageState(disabledMessageProp);
  }, [disabledProp, disabledMessageProp]);

  // Register with app-level registry on mount, unregister on unmount
  useEffect(() => {
    if (!tourData) return;
    regIdRef.current = registry.register(tourKey, {
      startTour,
      resetTour,
      disabled,
      disabledMessage,
    });
    return () => {
      if (regIdRef.current) {
        registry.unregister(regIdRef.current);
        regIdRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep registry entry in sync when disabled/message state changes
  useEffect(() => {
    if (regIdRef.current) {
      registry.update(regIdRef.current, { disabled, disabledMessage });
    }
  }, [disabled, disabledMessage, registry]);

  if (!tourData) {
    return children;
  }

  // Internacionalized locale for tour buttons
  const locale = {
    back: t("common:back"),
    close: t("common:close"),
    last: t("common:finish"),
    next: t("common:next"),
    skip: t("common:skipTour"),
  };

  const contextValue = {
    run,
    stepIndex,
    steps: tourData.steps,
    startTour,
    stopTour,
    resetTour,
    resetAllTours,
    goToStep,
    nextStep,
    setDisabled,
  };

  return (
    <TourContext.Provider value={contextValue}>
      <Joyride
        steps={tourData.steps}
        run={run}
        stepIndex={stepIndex}
        callback={handleJoyrideCallback}
        continuous={tourData.config.continuous}
        showProgress={tourData.config.showProgress}
        showBackButton={tourData.config.showBackButton}
        showSkipButton={tourData.config.showSkipButton}
        disableOverlayClose={tourData.config.disableOverlayClose}
        disableCloseOnEsc={tourData.config.disableCloseOnEsc}
        locale={locale}
        disableScrollParentFix={true}
        styles={tourStyles}
        tooltipComponent={CustomTooltip}
        scrollToFirstStep
        scrollOffset={100}
        floaterProps={{
          disableFlip: true,
        }}
      />
      {children}
    </TourContext.Provider>
  );
};
