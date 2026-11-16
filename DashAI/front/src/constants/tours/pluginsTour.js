import { Trans } from "react-i18next";
import GitHubIcon from "@mui/icons-material/GitHub";
import GppGoodOutlinedIcon from "@mui/icons-material/GppGoodOutlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { homeTourConfig } from "./homeTour";

const tipStyle = {
  backgroundColor: "rgba(76, 175, 80, 0.12)",
  color: "inherit",
  padding: "8px",
  borderRadius: "4px",
  marginTop: "10px",
  borderLeft: "3px solid #43A047",
};

// The card's icons, each with what it means, in a tip.
const iconSx = { fontSize: 16, verticalAlign: "text-bottom", mr: 0.5 };
const iconList = { margin: 0, padding: 0, listStyle: "none" };

// A target in the install dialog: inside its scrolling content (fixed on the
// page), Joyride 2.9 places the spotlight by the target's offset in the dialog
// unless it may unset that content's overflow (it doesn't scroll there).
// Scrolling the page never shows a fixed dialog better.
const inDialog = { disableScrollParentFix: false, disableScrolling: true };
const interactive = { spotlightClicks: true, isInteractive: true };
const titled = (key) => (
  <Trans i18nKey={key}>
    <div>
      <h3></h3>
      <p></p>
    </div>
  </Trans>
);

// Joyride 2.9 scrolls every step until its target is 100 px from the top, even
// when the step is in view (a jump on a long list, or a page opened
// scrolled). These steps scroll only when it isn't: the target below the app
// bar and above the bottom, with room for the tooltip on its side. Joyride
// reads `disableScrolling` as each step starts.
const TOOLTIP_ROOM = 400; // px: the tallest of these tooltips, about
const scrollIfHidden = (props) => {
  const step = { disableBeacon: true, ...props };
  return step.target === "body" || step.disableScrolling
    ? step
    : Object.defineProperty(step, "disableScrolling", {
        enumerable: true,
        get() {
          const rect = document
            .querySelector(step.target)
            ?.getBoundingClientRect();
          if (!rect) return false;
          const top =
            document.querySelector("header")?.getBoundingClientRect().bottom ??
            0;
          const above = step.placement === "top" ? TOOLTIP_ROOM : 0;
          const below = step.placement === "bottom" ? TOOLTIP_ROOM : 0;
          return (
            rect.top - above >= top && rect.bottom + below <= window.innerHeight
          );
        },
      });
};

// The store plugin the tour installs, and uninstalls at its end: shown only
// while the tour runs.
export const TOUR_PLUGIN = "sample-plugin";

// The user installs TOUR_PLUGIN, as the Hub's tour downloads iris:
// Plugins.jsx hides the tour while the preview downloads and while it
// installs, and resumes it once its next target shows. Opening the plugin
// then hands off to its page's tour. Without it in the store (offline, or
// another index) the tour ends before installing.
export const pluginsTourSteps = [
  {
    target: "body",
    content: titled("pluginsTour:pluginsModule"),
    placement: "center",
  },
  {
    target: '[data-tour="plugins-dev"]',
    content: titled("pluginsTour:developers"),
    placement: "bottom",
  },
  {
    target: '[data-tour="plugins-tabs"]',
    content: (
      <Trans i18nKey="pluginsTour:tabs">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    ...interactive,
  },
  {
    // The first card (a page of them is too tall to point at), or what is
    // shown instead of cards.
    target: '[data-tour="plugins-cards"]',
    content: (
      <Trans i18nKey="pluginsTour:cards">
        <div>
          <h3></h3>
          <p></p>
          <div style={tipStyle}>
            <ul style={iconList}>
              <li>
                <GppGoodOutlinedIcon
                  sx={{ ...iconSx, color: "primary.main" }}
                />
              </li>
              <li>
                <GitHubIcon sx={iconSx} />
              </li>
              <li>
                <WarningAmberIcon sx={{ ...iconSx, color: "warning.main" }} />
              </li>
            </ul>
          </div>
        </div>
      </Trans>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="plugins-install"]',
    content: (
      <Trans i18nKey="pluginsTour:install">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    ...interactive,
  },
  {
    target: '[data-tour="plugin-preview"]',
    content: (
      <Trans i18nKey="pluginsTour:preview">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBackButton: true,
    spotlightClicks: true, // its checkbox, when the level asks for it
    ...inDialog,
  },
  {
    target: '[data-tour="plugin-confirm"]',
    content: (
      <Trans i18nKey="pluginsTour:confirm">
        <div>
          <h3></h3>
          <p>
            <strong></strong>
          </p>
          <p style={tipStyle}></p>
        </div>
      </Trans>
    ),
    placement: "top",
    disableBackButton: true,
    ...interactive,
    ...inDialog,
  },
  {
    target: '[data-tour="plugins-installed"]',
    content: (
      <Trans i18nKey="pluginsTour:installed">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    disableBackButton: true,
    ...interactive,
  },
].map(scrollIfHidden);

// TOUR_PLUGIN's page, where the catalog's tour goes on: what an installed
// plugin's page shows, then the user opens its settings and uninstalls it.
// PluginsDetails.jsx resumes the tour once the settings load and once the
// confirm dialog opens; uninstalled, its last step shows in the catalog
// (Plugins.jsx). Other plugins' pages have no tour.
export const pluginSampleTourSteps = [
  {
    target: '[data-tour="plugin-detail-switch"]',
    content: titled("pluginsTour:detailSwitch"),
    placement: "bottom",
  },
  {
    target: '[data-tour="plugin-detail-trust"]',
    content: titled("pluginsTour:detailTrust"),
    placement: "auto",
  },
  {
    target: '[data-tour="plugin-detail-panel"]',
    content: (
      <Trans i18nKey="pluginsTour:detailPanel">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    // Beside the column, at its top: Joyride scrolls a "left" tooltip into
    // view, not the target, and on a column taller than the screen that hid
    // the column's top under the app bar.
    placement: "left-start",
  },
  {
    target: '[data-tour="plugin-detail-settings"]',
    content: (
      <Trans i18nKey="pluginsTour:sampleSettings">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    ...interactive,
  },
  {
    target: '[data-tour="plugin-settings-form"]',
    content: titled("pluginsTour:sampleSettingsForm"),
    placement: "bottom",
    disableBackButton: true,
  },
  {
    target: '[data-tour="plugin-detail-uninstall"]',
    content: (
      <Trans i18nKey="pluginsTour:sampleUninstall">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    ...interactive,
  },
  {
    target: '[data-tour="plugin-uninstall-confirm"]',
    content: (
      <Trans i18nKey="pluginsTour:sampleConfirm">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom", // above, it would hide what the dialog explains
    disableBackButton: true,
    ...interactive,
    ...inDialog,
  },
  {
    target: "body",
    content: (
      <Trans i18nKey="pluginsTour:sampleDone">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "center",
    disableBackButton: true,
  },
].map(scrollIfHidden);

export const pluginsTourConfig = homeTourConfig;
