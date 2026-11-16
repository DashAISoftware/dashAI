import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  AlertTitle,
  Box,
  Breadcrumbs,
  Button,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Link,
  Menu,
  MenuItem,
  Switch,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import UpgradeIcon from "@mui/icons-material/Upgrade";
import ReplayIcon from "@mui/icons-material/Replay";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  Link as RouterLink,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useSnackbar } from "notistack";
import { Trans, useTranslation } from "react-i18next";
import CustomLayout from "../../../components/custom/CustomLayout";
import {
  TourProvider,
  useTourContext,
} from "../../../components/tour/TourProvider";
import {
  isTourAtTarget,
  runWhenPresent,
  tourStepIndexOf,
} from "../../../components/tour/tourUtils";
import { TOUR_KEYS, TOUR_PLUGIN } from "../../../constants/tours";
import { useRememberedState } from "../../../hooks/useRememberedState";
import {
  getPluginReadme,
  getStoreReadme,
  pluginError,
  setPluginEnabled,
  uninstallPlugin,
} from "../../../api/plugins";
import PluginDialog from "./PluginDialog";
import PluginSettings from "./PluginSettings";
import Readme from "./Readme";
import DetailPanel, {
  AuthorSection,
  ComponentsSection,
  DependenciesSection,
  InstallationSection,
  RequiresSections,
  TrustSection,
} from "./DetailPanel";
import { VerifiedBadge } from "./PluginParts";
import {
  notifyPluginsChanged,
  useAnnounceInstalled,
  useInstalledPlugins,
  usePluginUpdates,
  useStore,
} from "../../../hooks/usePlugins";
import {
  asVersion,
  authorLine,
  canReinstall,
  canToggle,
  dependentsOf,
  errorMessage,
  pluginLinks,
  storePlugin,
  unmetDependencies,
} from "../pluginUtils";

const mono = { fontFamily: '"Geist Mono", monospace', fontSize: 13 };

function Back({ name }) {
  const { t } = useTranslation(["plugins"]);
  const [tab] = useRememberedState("plugins.tab", "explore");
  return (
    <Breadcrumbs sx={{ mb: 3 }}>
      <Link
        component={RouterLink}
        to="/app/plugins"
        underline="hover"
        color="text.secondary"
        sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
      >
        <ArrowBackIcon sx={{ fontSize: 16 }} />
        {t(`plugins:label.${tab}`)}
      </Link>
      {name && <Typography color="text.primary">{name}</Typography>}
    </Breadcrumbs>
  );
}
Back.propTypes = { name: PropTypes.string };

function Header({ plugin, children }) {
  const theme = useTheme();
  const author = authorLine(plugin);
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        alignItems: "start",
        columnGap: 2,
        pb: 3,
        mb: 3,
        borderBottom: `1px solid ${theme.palette.ui.border}`,
      }}
    >
      <Box>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            flexWrap: "wrap",
          }}
        >
          <Typography variant="h4" component="h1">
            {plugin.name}
          </Typography>
          {plugin.verified && <VerifiedBadge withLabel />}
        </Box>
        {author && (
          <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 0.5 }}>
            {author}
          </Typography>
        )}
      </Box>
      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        {children}
      </Box>
      {plugin.description && (
        <Typography
          sx={{
            gridColumn: { xs: "1 / -1", md: "1" },
            fontSize: 14,
            color: "text.secondary",
            mt: 1.5,
            maxWidth: 720,
          }}
        >
          {plugin.description}
        </Typography>
      )}
    </Box>
  );
}
Header.propTypes = {
  plugin: PropTypes.object.isRequired,
  children: PropTypes.node,
};

function Notice({ severity, code, values }) {
  const { t } = useTranslation(["plugins"]);
  return (
    <Alert severity={severity} variant="outlined" sx={{ mb: 3 }}>
      <AlertTitle>{t(`plugins:store.notice.${code}.title`)}</AlertTitle>
      {t(`plugins:store.notice.${code}.text`, values)}
    </Alert>
  );
}
Notice.propTypes = {
  severity: PropTypes.string.isRequired,
  code: PropTypes.string.isRequired,
  values: PropTypes.object,
};

function LinksMenu({ plugin }) {
  const theme = useTheme();
  const { t } = useTranslation(["plugins"]);
  const [anchor, setAnchor] = useState(null);
  const links = pluginLinks(plugin);
  if (!links.length) return null;
  return (
    <>
      <Tooltip title={t("plugins:button.moreOptions")}>
        <IconButton
          aria-label={t("plugins:button.moreOptions")}
          aria-haspopup="menu"
          aria-expanded={anchor ? "true" : "false"}
          onClick={(event) => setAnchor(event.currentTarget)}
          sx={{
            borderRadius: 1,
            border: `1px solid ${theme.palette.ui.border}`,
          }}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchor}
        open={!!anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {links.map(({ key, label, url }) => (
          <MenuItem
            key={url}
            component="a"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setAnchor(null)}
            sx={{ gap: 2, justifyContent: "space-between", fontSize: 14 }}
          >
            {key ? t(`plugins:link.${key}`) : label}
            <OpenInNewIcon sx={{ fontSize: 16, color: "text.secondary" }} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
LinksMenu.propTypes = { plugin: PropTypes.object.isRequired };

function Needs({ needs, link = false }) {
  const { t } = useTranslation(["plugins"]);
  const { store } = useStore();
  return needs.map(({ id, name, reason }) => {
    const listed = store?.plugins.find((entry) => entry.id === id);
    const to = link && (reason !== "uninstalled" || listed);
    return (
      <Box key={id}>
        <Trans
          t={t}
          i18nKey={`plugins:requires.${reason}`}
          values={{
            name: listed && reason === "uninstalled" ? listed.name : name,
          }}
          components={{
            // <link> is a void HTML element that Trans would leave empty
            plugin: to ? (
              <Link component={RouterLink} to={`/app/plugins/${id}`} />
            ) : (
              <span />
            ),
          }}
        />
      </Box>
    );
  });
}
Needs.propTypes = {
  needs: PropTypes.array.isRequired,
  link: PropTypes.bool,
};

function ProblemBox({ plugin, needs }) {
  const { t } = useTranslation(["plugins"]);
  const [details, setDetails] = useState(false);
  const { code, detail } = plugin.problem;
  return (
    <Alert severity="warning" variant="outlined" sx={{ mb: 3 }}>
      <AlertTitle>{t(`plugins:problem.${code}.title`)}</AlertTitle>
      {code === "dependency_unavailable" && needs.length ? (
        <Needs needs={needs} link />
      ) : (
        t(`plugins:problem.${code}.text`)
      )}
      {detail && (
        <Box>
          <Link
            component="button"
            onClick={() => setDetails(!details)}
            sx={{ fontSize: 12, mt: 1 }}
          >
            {t(
              details
                ? "plugins:button.hideDetails"
                : "plugins:button.showDetails",
            )}
          </Link>
          <Collapse in={details}>
            <Typography
              sx={{
                ...mono,
                fontSize: 12,
                mt: 1,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {detail}
            </Typography>
          </Collapse>
        </Box>
      )}
    </Alert>
  );
}
ProblemBox.propTypes = {
  plugin: PropTypes.object.isRequired,
  needs: PropTypes.array.isRequired,
};

function NameList({ names }) {
  return (
    // 1.5em fits the bullet, as an Alert clips what is outside
    <Box component="ul" sx={{ m: 0, mt: 1.5, pl: "1.5em", lineHeight: 1.7 }}>
      {names.map((name) => (
        <li key={name}>{name}</li>
      ))}
    </Box>
  );
}
NameList.propTypes = { names: PropTypes.array.isRequired };

function DetailBody({ readme, children }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) 300px" },
        gap: { xs: 4, md: 6 },
      }}
    >
      <Box component="article" sx={{ minWidth: 0 }}>
        {readme}
      </Box>
      <DetailPanel>{children}</DetailPanel>
    </Box>
  );
}
DetailBody.propTypes = { readme: PropTypes.node, children: PropTypes.node };

function useReadme(key, read) {
  const [readme, setReadme] = useState(undefined);
  useEffect(() => {
    if (!key) return undefined;
    let current = true;
    setReadme(undefined);
    read().then(
      (text) => current && setReadme(text),
      () => current && setReadme(false),
    );
    return () => {
      current = false;
    };
  }, [key]);
  return readme;
}

function useStoreReadme(entry) {
  const url = entry && {
    readme: `${entry.readme_base}README.md`,
    images: entry.readme_base,
    links: entry.readme_links,
  };
  const readmeUrl = url?.readme;
  return [useReadme(readmeUrl, () => getStoreReadme(readmeUrl)), url];
}

function StoreDetail({ id, fromStore }) {
  const { t } = useTranslation(["plugins"]);
  const navigate = useNavigate();
  const { store, loading } = useStore();
  const announce = useAnnounceInstalled();
  const [installing, setInstalling] = useState(false);
  const entry = store?.plugins.find((listed) => listed.id === id);
  const [readme, urls] = useStoreReadme(entry);
  const leave = fromStore && !loading && (!entry || entry.installed);
  useEffect(() => {
    if (leave) navigate(`/app/plugins/${id}`, { replace: true });
  }, [leave, id, navigate]);

  if (loading) {
    return (
      <CustomLayout>
        <Back />
      </CustomLayout>
    );
  }
  if (!entry) {
    return (
      <CustomLayout>
        <Back />
        <Typography>{t("plugins:detail.notFound")}</Typography>
      </CustomLayout>
    );
  }
  const plugin = storePlugin(entry);
  let notice = null;
  if (entry.installed_other) notice = ["info", "installedOther"];
  else if (!entry.offered) notice = ["warning", "requiresDashai"];
  else if (entry.offered !== entry.releases[0].tag) {
    notice = ["info", "olderOffered"];
  }
  const newest = {
    version: entry.releases[0].tag,
    dashai: entry.releases[0].min_app_version,
  };

  return (
    <CustomLayout>
      <Back name={plugin.name} />
      <Header plugin={plugin}>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          disabled={!entry.offered}
          onClick={() => setInstalling(true)}
        >
          {t("plugins:button.install")}
        </Button>
        <LinksMenu plugin={plugin} />
      </Header>
      {notice && (
        <Notice severity={notice[0]} code={notice[1]} values={newest} />
      )}
      <DetailBody
        readme={
          readme === false ? (
            <Typography sx={{ color: "text.secondary" }}>
              {t("plugins:store.readmeFailed")}
            </Typography>
          ) : (
            readme !== undefined && <Readme text={readme} urls={urls} />
          )
        }
      >
        <TrustSection plugin={plugin} before />
        <InstallationSection plugin={plugin} license={entry.license} />
        <ComponentsSection plugin={plugin} />
        <RequiresSections plugin={plugin} />
        <DependenciesSection plugin={plugin} />
        <AuthorSection plugin={plugin} />
      </DetailBody>
      <PluginDialog
        open={installing}
        mode="install"
        plugin={plugin}
        onClose={() => setInstalling(false)}
        onDone={(...done) => {
          setInstalling(false);
          announce(...done);
        }}
      />
    </CustomLayout>
  );
}
StoreDetail.propTypes = {
  id: PropTypes.string.isRequired,
  fromStore: PropTypes.bool,
};

function SampleTour({ on, children }) {
  if (!on) return children;
  return (
    <TourProvider tourKey={TOUR_KEYS.PLUGIN_SAMPLE}>{children}</TourProvider>
  );
}
SampleTour.propTypes = {
  on: PropTypes.bool.isRequired,
  children: PropTypes.node.isRequired,
};

function TourRef({ into }) {
  into.current = useTourContext();
  return null;
}
TourRef.propTypes = { into: PropTypes.object.isRequired };

export default function PluginsDetails() {
  const theme = useTheme();
  const { t, i18n } = useTranslation(["plugins"]);
  const { pluginId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { plugins, loading } = useInstalledPlugins();
  const { updates, needs_newer_dashai: needsNewerDashai = {} } =
    usePluginUpdates();
  const { store } = useStore();
  const announce = useAnnounceInstalled();
  const [dialog, setDialog] = useState(null); // "update" | "reinstall"
  const [uninstalling, setUninstalling] = useState(false);
  const [allowing, setAllowing] = useState(false); // "Turn on anyway?"
  const [asking, setAsking] = useState(null);
  const [busy, setBusy] = useState(false);
  const [switching, setSwitching] = useState(null); // the state just chosen
  const [tab, setTab] = useState("details");
  const tour = useRef(null); // its TourProvider's, set by TourRef

  const plugin = plugins.find(({ id }) => id === pluginId);
  const readme = useReadme(plugin && `${plugin.id}@${plugin.version}`, () =>
    getPluginReadme(plugin.id),
  );
  useEffect(() => setSwitching(null), [plugin]); // the list was read again

  if (loading) {
    return (
      <CustomLayout>
        <Back />
      </CustomLayout>
    );
  }
  const fromStore = params.get("store") === "1";
  if (!plugin || fromStore) {
    return <StoreDetail id={pluginId} fromStore={fromStore} />;
  }

  const entry = store?.plugins.find(
    (listed) => listed.id === plugin.id && listed.installed,
  );
  const newVersion = plugin.can_update ? updates[plugin.id] : null;
  const shown = plugin.has_settings ? tab : "details";

  const enabled = switching ?? plugin.active;
  const dependents = dependentsOf(plugins, plugin.id);
  const needs = unmetDependencies(plugin, plugins);
  const enabling = plugin.active ? [] : needs;
  const affected = plugin.active ? dependents : enabling;
  const toggle = async (allowBlocked = false, confirmed = false) => {
    if (busy) return;
    if (!plugin.active && plugin.problem?.code === "blocked" && !allowBlocked) {
      setAllowing(true);
      return;
    }
    setAllowing(false);
    if (affected.length && !confirmed) {
      setAsking({ allowBlocked });
      return;
    }
    setAsking(null);
    setBusy(true);
    setSwitching(!plugin.active);
    try {
      let restart = false;
      for (const need of enabling) {
        const turned = await setPluginEnabled(need.id, true).catch(() => null);
        if (turned?.problem?.code === "restart_required") {
          restart = true;
        } else if (!turned?.active) {
          setSwitching(null);
          notifyPluginsChanged();
          enqueueSnackbar(
            t("plugins:message.enableFailed", {
              dependency: need.name,
              name: plugin.name,
            }),
            { variant: "error" },
          );
          return;
        }
      }
      const updated = await setPluginEnabled(plugin.id, !plugin.active, {
        allowBlocked,
      });
      setSwitching(updated.active); // the backend's answer, until the reread
      notifyPluginsChanged();
      if (!plugin.active && !updated.active) {
        // e.g. it still fails to load in the job worker
        const code = restart
          ? "restart_required"
          : (updated.problem?.code ?? "load_failed");
        enqueueSnackbar(t(`plugins:problem.${code}.title`), {
          variant: "warning",
        });
        return;
      }
      enqueueSnackbar(
        t(
          updated.active
            ? enabling.length
              ? "plugins:message.enabledWith"
              : "plugins:message.enabled"
            : "plugins:message.disabled",
          {
            name: plugin.name,
            names: new Intl.ListFormat(i18n.language).format(
              enabling.map(({ name }) => name),
            ),
          },
        ),
        { variant: "info" },
      );
    } catch (failure) {
      setSwitching(null);
      enqueueSnackbar(errorMessage(t, pluginError(failure)), {
        variant: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  const uninstall = async () => {
    setBusy(true);
    try {
      await uninstallPlugin(plugin.id);
      enqueueSnackbar(t("plugins:message.uninstalled", { name: plugin.name }), {
        variant: "info",
      });
      notifyPluginsChanged();
      const guided = isTourAtTarget(tour.current, "plugin-uninstall-confirm");
      if (guided) tour.current.handoffTour(tour.current.steps.length - 1);
      navigate("/app/plugins", { state: { tourEnds: guided } });
    } catch (failure) {
      enqueueSnackbar(errorMessage(t, pluginError(failure)), {
        variant: "error",
      });
      setBusy(false);
      setUninstalling(false);
    }
  };

  const goOn = (from, to) => {
    const current = tour.current;
    if (!isTourAtTarget(current, from)) return;
    current.stopTour();
    runWhenPresent(`[data-tour="${to}"]`, () =>
      current.resumeAtStep(tourStepIndexOf(current, to)),
    );
  };
  const askUninstall = () => {
    setUninstalling(true);
    goOn("plugin-detail-uninstall", "plugin-uninstall-confirm");
  };
  const closeUninstall = () => {
    setUninstalling(false);
    if (isTourAtTarget(tour.current, "plugin-uninstall-confirm")) {
      tour.current.stopTour(); // kept installed, the tour ends unfinished
    }
  };

  return (
    <CustomLayout>
      <SampleTour on={plugin.id === TOUR_PLUGIN}>
        <TourRef into={tour} />
        <Back name={plugin.name} />
        <Header plugin={plugin}>
          <Tooltip
            title={
              plugin.problem?.code === "load_failed" ? (
                t("plugins:label.retryLoadHelp")
              ) : canToggle(plugin, plugins) ? (
                t("plugins:label.toggleHelp")
              ) : plugin.problem &&
                plugin.problem.code !== "dependency_unavailable" ? (
                t(`plugins:problem.${plugin.problem.code}.title`)
              ) : (
                <Needs
                  needs={needs.filter(({ reason }) => reason !== "disabled")}
                />
              )
            }
          >
            {/* The box fits the text, so the switch stays put */}
            <FormControlLabel
              data-tour="plugin-detail-switch"
              labelPlacement="start"
              sx={{
                m: 0,
                pl: "12px", // as wide as the Switch's own inset
                border: `1px solid ${theme.palette.ui.border}`,
                borderRadius: 1,
              }}
              control={
                <Switch
                  checked={enabled}
                  onChange={() => toggle()}
                  disabled={!canToggle(plugin, plugins)}
                />
              }
              label={t(
                enabled ? "plugins:label.enabled" : "plugins:label.disabled",
              )}
            />
          </Tooltip>
          {newVersion && (
            <Button
              variant="outlined"
              startIcon={<UpgradeIcon />}
              onClick={() => setDialog("update")}
            >
              {t("plugins:button.updateTo", { version: asVersion(newVersion) })}
            </Button>
          )}
          {canReinstall(plugin, newVersion) && (
            <Button
              variant="outlined"
              startIcon={<ReplayIcon />}
              onClick={() => setDialog("reinstall")}
            >
              {t("plugins:button.reinstall")}
            </Button>
          )}
          <Button
            data-tour="plugin-detail-uninstall"
            variant="outlined"
            color="error"
            startIcon={<DeleteOutlineIcon />}
            onClick={askUninstall}
          >
            {t("plugins:button.uninstall")}
          </Button>
          <LinksMenu plugin={plugin} />
        </Header>

        {plugin.problem?.code === "blocked" ? (
          <Notice severity="error" code="blocked" />
        ) : plugin.problem ? (
          <ProblemBox plugin={plugin} needs={needs} />
        ) : plugin.removed === "critical" ? (
          <Notice severity="warning" code="allowedAnyway" />
        ) : plugin.removed ? (
          <Notice severity="info" code="removed" />
        ) : (
          needsNewerDashai[plugin.id] &&
          entry && (
            <Notice
              severity="info"
              code="newerNeedsDashai"
              values={{
                version: entry.releases[0].tag,
                dashai: entry.releases[0].min_app_version,
              }}
            />
          )
        )}

        {plugin.has_settings && (
          <Tabs
            value={shown}
            onChange={(event, value) => {
              setTab(value);
              goOn("plugin-detail-settings", "plugin-settings-form");
            }}
            sx={{ mb: 3, borderBottom: `1px solid ${theme.palette.ui.border}` }}
          >
            <Tab value="details" label={t("plugins:tabs.details")} />
            <Tab
              value="settings"
              label={t("plugins:tabs.settings")}
              data-tour="plugin-detail-settings"
            />
          </Tabs>
        )}

        {shown === "details" && (
          <DetailBody
            readme={
              readme !== undefined && (
                <Readme
                  text={readme || null}
                  urls={
                    plugin.readme_base && {
                      images: plugin.readme_base,
                      links: plugin.readme_links,
                    }
                  }
                />
              )
            }
          >
            <TrustSection plugin={plugin} />
            <InstallationSection plugin={plugin} license={entry?.license} />
            <ComponentsSection plugin={plugin} />
            <RequiresSections plugin={plugin} />
            <DependenciesSection plugin={plugin} />
            <AuthorSection plugin={plugin} />
          </DetailBody>
        )}
        {plugin.has_settings && (
          <Box sx={{ maxWidth: 860 }}>
            <PluginSettings plugin={plugin} shown={shown === "settings"} />
          </Box>
        )}

        <PluginDialog
          open={!!dialog}
          mode={dialog ?? "update"}
          plugin={plugin}
          updateRef={newVersion}
          onClose={() => setDialog(null)}
          onDone={(...done) => {
            setDialog(null);
            announce(...done);
          }}
        />
        <Dialog
          open={uninstalling}
          onClose={() => !busy && closeUninstall()}
          maxWidth="xs"
          fullWidth
          slotProps={{ paper: { sx: { backgroundImage: "none" } } }}
        >
          <DialogTitle>{t("plugins:uninstall.title")}</DialogTitle>
          <DialogContent>
            <Typography>
              {t("plugins:uninstall.text", { name: plugin.name })}
            </Typography>
            {dependents.length > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {t("plugins:requires.uninstallText")}
                <NameList names={dependents.map(({ name }) => name)} />
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={closeUninstall} disabled={busy}>
              {t("plugins:button.cancel")}
            </Button>
            <Button
              data-tour="plugin-uninstall-confirm"
              color="error"
              onClick={uninstall}
              disabled={busy}
            >
              {t(
                busy
                  ? "plugins:button.uninstalling"
                  : "plugins:button.uninstall",
              )}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          open={allowing}
          onClose={() => setAllowing(false)}
          maxWidth="xs"
          fullWidth
          slotProps={{ paper: { sx: { backgroundImage: "none" } } }}
        >
          <DialogTitle>
            {t("plugins:allowBlocked.title", { name: plugin.name })}
          </DialogTitle>
          <DialogContent>
            <Typography>{t("plugins:allowBlocked.text")}</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAllowing(false)}>
              {t("plugins:button.cancel")}
            </Button>
            <Button color="error" onClick={() => toggle(true)}>
              {t("plugins:allowBlocked.confirm")}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          open={!!asking}
          onClose={() => setAsking(null)}
          maxWidth="xs"
          fullWidth
          slotProps={{ paper: { sx: { backgroundImage: "none" } } }}
        >
          <DialogTitle>
            {t(
              plugin.active
                ? "plugins:requires.disableTitle"
                : "plugins:requires.enableTitle",
              { name: plugin.name },
            )}
          </DialogTitle>
          <DialogContent>
            <Typography>
              {plugin.active
                ? t("plugins:requires.disableText")
                : t("plugins:requires.enableText", {
                    name: plugin.name,
                    count: enabling.length,
                  })}
            </Typography>
            <NameList names={affected.map(({ name }) => name)} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAsking(null)}>
              {t("plugins:button.cancel")}
            </Button>
            <Button
              variant="contained"
              onClick={() => toggle(!!asking?.allowBlocked, true)}
            >
              {t(
                plugin.active
                  ? "plugins:button.disable"
                  : "plugins:button.enable",
              )}
            </Button>
          </DialogActions>
        </Dialog>
      </SampleTour>
    </CustomLayout>
  );
}
