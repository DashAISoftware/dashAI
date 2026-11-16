import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  IconButton,
  Tab,
  TablePagination,
  Tabs,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import CodeIcon from "@mui/icons-material/Code";
import PowerOutlinedIcon from "@mui/icons-material/PowerOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useSnackbar } from "notistack";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import CustomLayout from "../../components/custom/CustomLayout";
import CountBadge from "../../components/shared/CountBadge";
import {
  TourProvider,
  useTourContext,
} from "../../components/tour/TourProvider";
import {
  isTourAtTarget,
  runWhenPresent,
  tourStepIndexOf,
} from "../../components/tour/tourUtils";
import { TOUR_KEYS, TOUR_PLUGIN } from "../../constants/tours";
import { useRememberedState } from "../../hooks/useRememberedState";
import PluginsCard from "./components/PluginsCard";
import PluginsToolbar from "./components/PluginsToolbar";
import PluginDialog from "./components/PluginDialog";
import {
  useAnnounceInstalled,
  useInstalledPlugins,
  usePluginUpdates,
  useStore,
} from "../../hooks/usePlugins";
import {
  NO_FILTERS,
  PAGE_SIZES,
  errorMessage,
  filterPlugins,
  savedPageSize,
  sortPlugins,
  storePlugin,
  updatesMessage,
} from "./pluginUtils";

const Message = ({ children, color = "text.secondary", tour }) => (
  <Typography data-tour={tour} sx={{ color, py: 4, textAlign: "center" }}>
    {children}
  </Typography>
);
Message.propTypes = {
  children: PropTypes.node,
  color: PropTypes.string,
  tour: PropTypes.string,
};

function PluginList({ view, children }) {
  if (view === "list") {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {children}
      </Box>
    );
  }
  return (
    <Box
      sx={{
        display: "grid",
        gap: 2,
        gridAutoRows: "1fr", // every row as tall as the tallest card
        gridTemplateColumns: {
          xs: "1fr",
          md: "repeat(2, 1fr)",
          xl: "repeat(3, 1fr)",
        },
      }}
    >
      {children}
    </Box>
  );
}
PluginList.propTypes = {
  view: PropTypes.string.isRequired,
  children: PropTypes.node,
};

function StoreUnread({ store }) {
  const { t } = useTranslation(["plugins"]);
  const failed =
    {
      rate_limited: "plugins:store.rateLimited", // a token doesn't help raw
      invalid_store: "plugins:store.invalid",
      unverified_store: "plugins:store.unverified",
    }[store?.error] ?? "plugins:store.readFailed";
  return (
    <Message color={store?.checking ? undefined : "error"}>
      {t(store?.checking ? "plugins:store.reading" : failed)}
    </Message>
  );
}
StoreUnread.propTypes = { store: PropTypes.object };

const forTour = (plugin) => plugin.fromStore && plugin.id === TOUR_PLUGIN;

function PluginsTab({
  tab,
  plugins,
  updates,
  sortBy,
  onSortByChange,
  view,
  onViewChange,
  onInstall,
  tourPlugin,
}) {
  const { t } = useTranslation(["plugins"]);
  const top = useRef(null);
  const [filters, setFilters] = useRememberedState(
    `plugins.filters.${tab}`,
    NO_FILTERS,
  );
  const [page, setPage] = useRememberedState(`plugins.page.${tab}`, 0);
  const [size, setSize] = useState(savedPageSize);
  const shown = sortPlugins(
    filterPlugins(plugins, filters, updates),
    sortBy,
  ).sort((a, b) => forTour(b) - forTour(a));
  const pages = Math.max(1, Math.ceil(shown.length / size));
  const current = Math.min(page, pages - 1);
  const variant = view === "list" ? "row" : "card";
  const visible = shown.slice(current * size, (current + 1) * size);
  const first = visible.find((plugin) => forTour(plugin) && plugin.offered);

  return (
    <>
      <Box ref={top} sx={{ scrollMarginTop: 80 }}>
        <PluginsToolbar
          tab={tab}
          plugins={plugins}
          updates={updates}
          filters={filters}
          onFiltersChange={(value) => {
            setFilters(value);
            setPage(0);
          }}
          sortBy={sortBy}
          onSortByChange={(value) => {
            onSortByChange(value);
            setPage(0);
          }}
          view={view}
          onViewChange={onViewChange}
          shown={shown.length}
        />
      </Box>
      {shown.length ? (
        <PluginList view={view}>
          {visible.map((plugin) =>
            plugin.fromStore ? (
              <PluginsCard
                key={`store-${plugin.id}`}
                plugin={plugin}
                variant={variant}
                tour={plugin === visible[0] ? "plugins-cards" : undefined}
                to={
                  plugin.installed_other
                    ? `/app/plugins/${plugin.id}?store=1`
                    : null
                }
                action={
                  <Button
                    data-tour={plugin === first ? "plugins-install" : undefined}
                    size="small"
                    variant="outlined"
                    aria-label={t("plugins:button.installNamed", {
                      name: plugin.name,
                    })}
                    disabled={!plugin.offered}
                    onClick={() => onInstall(plugin)}
                    sx={{ flexShrink: 0 }}
                  >
                    {t("plugins:button.install")}
                  </Button>
                }
              />
            ) : (
              <PluginsCard
                key={plugin.id}
                plugin={plugin}
                newVersion={updates[plugin.id]}
                variant={variant}
                tour={
                  plugin.id === tourPlugin
                    ? "plugins-installed"
                    : plugin === visible[0]
                      ? "plugins-cards"
                      : undefined
                }
              />
            ),
          )}
        </PluginList>
      ) : (
        <Message tour="plugins-cards">{t("plugins:empty.noMatches")}</Message>
      )}
      {/* Shown even on one page, so the size picker stays reachable */}
      {shown.length > PAGE_SIZES[0] && (
        <TablePagination
          component="div"
          count={shown.length}
          page={current}
          rowsPerPage={size}
          rowsPerPageOptions={PAGE_SIZES}
          onRowsPerPageChange={(event) => {
            localStorage.setItem("plugins.pageSize", event.target.value);
            setSize(Number(event.target.value));
            setPage(0);
          }}
          labelRowsPerPage={t("plugins:label.perPage")}
          onPageChange={(event, value) => {
            setPage(value);
            top.current?.scrollIntoView?.({ block: "start" });
          }}
          labelDisplayedRows={({ from, to, count }) =>
            t("plugins:label.pageRange", { from, to, count })
          }
        />
      )}
    </>
  );
}
PluginsTab.propTypes = {
  tab: PropTypes.string.isRequired,
  plugins: PropTypes.array.isRequired,
  updates: PropTypes.object.isRequired,
  sortBy: PropTypes.string.isRequired,
  onSortByChange: PropTypes.func.isRequired,
  view: PropTypes.string.isRequired,
  onViewChange: PropTypes.func.isRequired,
  onInstall: PropTypes.func.isRequired,
  tourPlugin: PropTypes.string,
};

function Catalog({ ending }) {
  const theme = useTheme();
  const { t } = useTranslation(["plugins"]);
  const { enqueueSnackbar } = useSnackbar();
  const { plugins, loading, error } = useInstalledPlugins();
  const { store, loading: storeLoading } = useStore();
  const updates = usePluginUpdates();
  const announce = useAnnounceInstalled();
  const [sortBy, setSortBy] = useRememberedState("plugins.sortBy", "newest");
  const [view, setView] = useRememberedState("plugins.view", "grid");
  const [tab, setTab] = useRememberedState("plugins.tab", "explore");
  const [developing, setDeveloping] = useState(false);
  const [installing, setInstalling] = useState(null);
  // A fresh dialog each time, so it never shows the last preview
  const [installs, setInstalls] = useState(0);
  const tour = useTourContext();
  const tourRef = useRef(tour);
  tourRef.current = tour;
  const guided = useRef(null);
  const [tourPlugin, setTourPlugin] = useState(null);

  const available = (store?.plugins ?? [])
    .filter(
      (entry) =>
        !entry.installed &&
        ((tour.run && !ending) ||
          installing?.id === entry.id ||
          entry.id !== TOUR_PLUGIN),
    )
    .map(storePlugin);
  const pool = {
    explore: available,
    installed: plugins,
  }[tab];
  const updateCount = Object.keys(updates.updates).length;
  const narrow = useMediaQuery(theme.breakpoints.down("md"));
  const checkLabel = t(
    updates.checking
      ? "plugins:button.checkingUpdates"
      : "plugins:button.checkUpdates",
  );

  const resumeAt = (name) => {
    tour.stopTour();
    return runWhenPresent(`[data-tour="${name}"]`, () =>
      tour.resumeAtStep(tourStepIndexOf(tour, name)),
    );
  };
  const install = (plugin) => {
    setInstalling(plugin);
    setInstalls((count) => count + 1);
    if (isTourAtTarget(tour, "plugins-install")) {
      guided.current = resumeAt("plugin-preview");
    }
  };
  const installed = (plugin, verb, also) => {
    setInstalling(null);
    announce(plugin, verb, also);
    if (!guided.current) return;
    guided.current = null;
    setTab("installed");
    setTourPlugin(plugin.id);
    resumeAt("plugins-installed");
  };
  const closeInstall = () => {
    setInstalling(null);
    if (!guided.current) return;
    guided.current(); // closed without installing, the tour stays hidden
    guided.current = null;
    tour.stopTour();
  };

  const installable = available.some(
    (plugin) => forTour(plugin) && plugin.offered,
  );
  const storeSettled = !storeLoading && !store?.checking;
  useEffect(() => {
    if (
      isTourAtTarget(tour, "plugins-install") &&
      storeSettled &&
      !installable
    ) {
      tour.completeTour();
    }
  }, [tour, storeSettled, installable]);
  const navigate = useNavigate();
  const ended = ending && !tour.run && tour.stepIndex >= tour.steps.length - 1;
  useEffect(() => {
    if (ended) navigate("/app/plugins", { replace: true });
  }, [ended, navigate]);
  useEffect(
    () => () => {
      const current = tourRef.current;
      if (!isTourAtTarget(current, "plugins-installed")) return;
      current.markTourAsCompleted();
      current.handoffTour(0, TOUR_KEYS.PLUGIN_SAMPLE);
    },
    [],
  );

  const checkUpdates = async () => {
    const { status, error: failure } = await updates.check();
    if (failure) {
      enqueueSnackbar(errorMessage(t, failure), { variant: "error" });
      return;
    }
    const [variant, key, params] = updatesMessage(status);
    enqueueSnackbar(t(`plugins:message.${key}`, params), { variant });
  };

  const empty = (
    <Box
      sx={{
        border: `1px dashed ${theme.palette.ui.borderDark}`,
        borderRadius: 1,
        py: 8,
        px: 2,
        textAlign: "center",
      }}
    >
      <PowerOutlinedIcon sx={{ fontSize: 32, color: "text.secondary" }} />
      <Typography sx={{ fontWeight: 600, mt: 1 }}>
        {t("plugins:empty.title")}
      </Typography>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 1, mb: 2 }}>
        {t("plugins:empty.text")}
      </Typography>
      <Button variant="outlined" onClick={() => setDeveloping(true)}>
        {t("plugins:button.installPlugin")}
      </Button>
    </Box>
  );

  const storeRead = !!store?.built_at;
  const waiting = {
    explore: storeLoading,
    installed: loading,
  }[tab];
  let content = null; // while reading, the lists answer fast so no placeholder
  let listed = false; // cards (or no matches), the tour points at those
  if (waiting) {
    content = null;
  } else if (tab === "installed" && error) {
    content = <Typography color="error">{errorMessage(t, error)}</Typography>;
  } else if (tab === "explore" && !storeRead && store?.error !== "disabled") {
    content = <StoreUnread store={store} />;
  } else if (tab === "explore" && !store.plugins.length) {
    content = <Message>{t("plugins:store.empty")}</Message>;
  } else if (tab === "explore" && !pool.length) {
    content = <Message>{t("plugins:store.allInstalled")}</Message>;
  } else if (!pool.length) {
    content = empty;
  } else {
    listed = true;
    content = (
      <PluginsTab
        key={tab}
        tab={tab}
        plugins={pool}
        updates={updates.updates}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        view={view}
        onViewChange={setView}
        onInstall={install}
        tourPlugin={tourPlugin}
      />
    );
  }

  return (
    <CustomLayout>
      {/* Two columns, the developers' block under the subtitle on a phone */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "minmax(0, 1fr) auto" },
          alignItems: "end",
          columnGap: 6,
          rowGap: 3,
          mb: 4,
        }}
      >
        <Box>
          <Typography variant="h4" component="h1" sx={{ mb: 6 }}>
            {t("plugins:title")}
          </Typography>
          <Typography variant="h6" component="h2">
            {t("plugins:subtitle")}
          </Typography>
        </Box>
        <Box
          data-tour="plugins-dev"
          sx={{ textAlign: "right", justifySelf: "end" }}
        >
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            {t("plugins:dev.question")}
          </Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            {t("plugins:dev.hint")}
          </Typography>
          <Button
            size="small"
            startIcon={<CodeIcon />}
            onClick={() => setDeveloping(true)}
            sx={{ mt: 0.5, mr: -0.625 }}
          >
            {t("plugins:button.devPlugin")}
          </Button>
        </Box>
      </Box>

      <Box
        data-tour="plugins-tabs"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          mb: 3,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
        }}
      >
        <Tabs
          value={tab}
          onChange={(event, value) => setTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ flexGrow: 1, minWidth: 0 }}
        >
          <Tab
            value="explore"
            label={t("plugins:label.explore")}
            onClick={() => {
              if (isTourAtTarget(tour, "plugins-tabs")) tour.nextStep();
            }}
          />
          <Tab
            value="installed"
            label={
              <Box
                component="span"
                sx={{ display: "inline-flex", alignItems: "center" }}
              >
                {t("plugins:label.installed")}
                <CountBadge
                  count={updateCount}
                  title={t("plugins:label.updatesAvailable", {
                    count: updateCount,
                  })}
                />
              </Box>
            }
          />
        </Tabs>
        {/* Rereads the store and updates, icon only on a narrow window */}
        {narrow ? (
          <Tooltip title={checkLabel}>
            <span>
              <IconButton
                color="primary"
                aria-label={checkLabel}
                onClick={checkUpdates}
                disabled={updates.checking}
              >
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
        ) : (
          <Button
            startIcon={<RefreshIcon />}
            onClick={checkUpdates}
            disabled={updates.checking}
            sx={{ flexShrink: 0 }}
          >
            {checkLabel}
          </Button>
        )}
      </Box>

      {/* Always there, whatever it shows, as the tour points here. */}
      <Box data-tour={listed ? undefined : "plugins-cards"}>{content}</Box>

      <PluginDialog
        open={developing}
        mode="install"
        onClose={() => setDeveloping(false)}
        onDone={(...done) => {
          setDeveloping(false);
          announce(...done);
        }}
      />
      <PluginDialog
        key={installs}
        open={!!installing}
        mode="install"
        plugin={installing}
        onClose={closeInstall}
        onDone={installed}
      />
    </CustomLayout>
  );
}

Catalog.propTypes = { ending: PropTypes.bool.isRequired };

export default function PluginsPage() {
  const ending = !!useLocation().state?.tourEnds;
  const tourKey = ending ? TOUR_KEYS.PLUGIN_SAMPLE : TOUR_KEYS.PLUGINS;
  return (
    <TourProvider key={tourKey} tourKey={tourKey}>
      <Catalog ending={ending} />
    </TourProvider>
  );
}
