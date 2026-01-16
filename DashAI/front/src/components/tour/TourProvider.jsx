import React, { createContext, useContext } from "react";
import Joyride from "react-joyride";
import { useTranslation } from "react-i18next";
import { useTour } from "../../hooks/useTour";
import { tours } from "../../constants/tours";
import { tourStyles } from "./tourStyles";

const TourContext = createContext(null);
export const useTourContext = () => useContext(TourContext);

export const TourProvider = ({ tourKey, children }) => {
  const { t } = useTranslation(["common"]);
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
        styles={tourStyles}
        scrollToFirstStep
        scrollOffset={100}
      />
      {children}
    </TourContext.Provider>
  );
};
