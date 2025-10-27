import React, { createContext, useContext, useEffect } from "react";
import Joyride from "react-joyride";
import { useTour } from "../../hooks/useTour";
import { tours } from "../../constants/tours";
import { tourStyles } from "./tourStyles";

const TourContext = createContext(null);
export const useTourContext = () => useContext(TourContext);

export const TourProvider = ({ tourKey, children }) => {
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
        locale={tourData.config.locale}
        styles={tourStyles}
        scrollToFirstStep
        scrollOffset={100}
      />
      {children}
    </TourContext.Provider>
  );
};
