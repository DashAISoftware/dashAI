import { Trans } from "react-i18next";

export const generativeTourSteps = [
  {
    target: "body",
    content: (
      <Trans i18nKey="generativeTour:generativeModule">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "center",
    disableBeacon: true,
  },
];

export const generativeTourConfig = {
  continuous: true,
  showProgress: true,
  showBackButton: true,
  showSkipButton: true,
  disableOverlayClose: true,
  disableCloseOnEsc: false,
};
