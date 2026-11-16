import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import JSZip from "jszip";
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  LinearProgress,
  Link,
  TextField,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import CheckIcon from "@mui/icons-material/Check";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  discardPreview,
  installPreview,
  pluginError,
  previewRemote,
  previewUpload,
  setPluginEnabled,
  updatePlugin,
} from "../../../api/plugins";
import CredentialsDialog from "../../../components/credentials/CredentialsDialog";
import { useTourContext } from "../../../components/tour/TourProvider";
import { isTourAtTarget } from "../../../components/tour/tourUtils";
import {
  notifyPluginsChanged,
  useInstalledPlugins,
} from "../../../hooks/usePlugins";
import { InfoRows, TrustNotice } from "./PluginParts";
import {
  asVersion,
  canUpdateTo,
  errorList,
  errorMessage,
  trustText,
  versionNotice,
} from "../pluginUtils";

const readEntry = async (entry, prefix = "") => {
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) =>
      entry.file(resolve, reject),
    );
    return [{ path: prefix + entry.name, file }];
  }
  const reader = entry.createReader();
  const children = [];
  // readEntries returns at most ~100 entries per call.
  for (;;) {
    const batch = await new Promise((resolve, reject) =>
      reader.readEntries(resolve, reject),
    );
    if (!batch.length) break;
    children.push(...batch);
  }
  const nested = await Promise.all(
    children.map((child) => readEntry(child, `${prefix}${entry.name}/`)),
  );
  return nested.flat();
};

const zipFiles = async (files) => {
  const zip = new JSZip();
  files.forEach(({ path, file }) => zip.file(path, file));
  return zip.generateAsync({ type: "blob" });
};

function ErrorBox({ error, title }) {
  const { t } = useTranslation(["plugins"]);
  const errors = errorList(error);
  return (
    <Alert severity="error" variant="outlined">
      <AlertTitle>{title}</AlertTitle>
      {errors.length === 1 ? (
        errorMessage(t, errors[0])
      ) : (
        <Box component="ul" sx={{ m: 0, pl: 2 }}>
          {errors.map((item, index) => (
            <li key={index}>{errorMessage(t, item)}</li>
          ))}
        </Box>
      )}
    </Alert>
  );
}
ErrorBox.propTypes = {
  error: PropTypes.object.isRequired,
  title: PropTypes.string,
};

function ResultBox({ older }) {
  const { t } = useTranslation(["plugins"]);
  const theme = useTheme();
  return (
    <Box
      sx={{
        display: "flex",
        gap: 1.5,
        p: 2,
        borderRadius: 1,
        border: `1px solid ${theme.palette.ui.border}`,
      }}
    >
      {older ? (
        <InfoOutlinedIcon sx={{ color: "text.secondary" }} />
      ) : (
        <CheckIcon sx={{ color: "success.main" }} />
      )}
      <Typography sx={{ fontWeight: 500 }}>
        {t(
          older
            ? "plugins:dialog.version.olderUpdate"
            : "plugins:dialog.upToDate",
        )}
      </Typography>
    </Box>
  );
}
ResultBox.propTypes = { older: PropTypes.bool.isRequired };

// Install, update or reinstall dialog, pick > review > working > done
export default function PluginDialog({
  open,
  onClose,
  onDone,
  mode,
  plugin,
  updateRef = null,
}) {
  const theme = useTheme();
  const { t, i18n } = useTranslation(["plugins"]);
  const { enqueueSnackbar } = useSnackbar();
  const tour = useTourContext();
  const fromRemote = !!plugin?.can_update;
  // Values, as a reread of the list must not restart an open dialog
  const location = plugin?.location;
  const installedRef = plugin?.ref;
  const [step, setStep] = useState("pick");
  const [candidate, setCandidate] = useState(null); // {kind, blob, name, location}
  const [preview, setPreview] = useState(null);
  const [fromStore, setFromStore] = useState([]); // [{need, preview}]
  const [ack, setAck] = useState(false);
  const [error, setError] = useState(null);
  const [remoteUrl, setRemoteUrl] = useState("");
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const zipInput = useRef(null);
  const folderInput = useRef(null);
  const kept = useRef([]);
  const forget = useCallback(() => {
    kept.current.forEach((token) => discardPreview(token));
    kept.current = [];
  }, []);
  useEffect(() => forget, [forget]); // leaving the page with it open
  // The review whose answer counts. Closing or reviewing again ends it.
  const reviewing = useRef(0);

  const review = useCallback(
    async (next) => {
      forget();
      const mine = ++reviewing.current;
      setCandidate(next);
      setStep("loading");
      setAck(false);
      try {
        const result =
          next.kind === "remote"
            ? await previewRemote(next.location, next.ref)
            : await previewUpload(next.blob, next.name);
        const upToDate =
          mode === "update" &&
          result.is_valid &&
          !canUpdateTo(result, installedRef);
        const needs =
          result.is_valid && !upToDate
            ? (result.plugin_dependencies ?? []).filter(
                ({ state }) => state === "store",
              )
            : [];
        const settled = await Promise.allSettled(
          needs.map(({ location: at, ref }) => previewRemote(at, ref)),
        );
        const previews = [result, ...settled.map(({ value }) => value)];
        const tokens = previews.map((p) => p?.preview).filter(Boolean);
        if (mine !== reviewing.current) {
          tokens.forEach((token) => discardPreview(token));
          return;
        }
        kept.current = tokens;
        if (upToDate) forget();
        const failed = settled.find(({ status }) => status === "rejected");
        if (failed) throw failed.reason;
        setPreview(result);
        setFromStore(
          needs.map((need, index) => ({ need, preview: previews[index + 1] })),
        );
        setStep(upToDate ? "upToDate" : "review");
      } catch (failure) {
        if (mine !== reviewing.current) return;
        setError(pluginError(failure));
        setStep("failed");
      }
    },
    [mode, installedRef, forget],
  );

  // A GitHub plugin skips pick, previewing the offered, installed or store tag
  useEffect(() => {
    if (!open) return;
    setError(null);
    setPreview(null);
    setFromStore([]);
    if (fromRemote) {
      review({
        kind: "remote",
        location,
        ref: mode === "update" ? updateRef : installedRef,
      });
    } else {
      setStep("pick");
      setCandidate(null);
      setRemoteUrl("");
    }
  }, [open, fromRemote, location, installedRef, updateRef, mode, review]);

  const pickZip = (file) =>
    file && review({ kind: "zip", blob: file, name: file.name });
  const pickFolder = async (files) => {
    if (!files.length) return;
    const root = files[0].path.split("/")[0];
    review({ kind: "zip", blob: await zipFiles(files), name: `${root}.zip` });
  };

  const onDrop = async (event) => {
    event.preventDefault();
    setDragging(false);
    const entry = event.dataTransfer.items?.[0]?.webkitGetAsEntry?.();
    if (entry?.isDirectory) {
      pickFolder(await readEntry(entry));
    } else {
      pickZip(event.dataTransfer.files[0]);
    }
  };

  const confirm = async () => {
    if (isTourAtTarget(tour, "plugin-confirm")) tour.stopTour();
    setStep("working");
    const also = []; // the names of those installed before it
    try {
      for (const need of needs) {
        if (need.state === "store") {
          const { preview: token } = fromStore.find(
            (reviewed) => reviewed.need.id === need.id,
          ).preview;
          await installPreview(token);
          kept.current = kept.current.filter((other) => other !== token);
          also.push(need.name);
        } else if (need.state === "disabled" && !isInstalled) {
          await setPluginEnabled(need.id, true);
        }
      }
      const installed =
        candidate.kind === "remote" && updating && verb === "update"
          ? await updatePlugin(plugin.id, preview.preview)
          : await installPreview(preview.preview);
      kept.current = [];
      onDone(installed, verb, also);
    } catch (failure) {
      setError(pluginError(failure));
      setStep("failed");
      if (!needs.some(({ state }) => state !== "active")) return;
      notifyPluginsChanged(); // some may be installed or on now
      setPreview(null); // retrying reviews it again, what it needs changed
      if (also.length) {
        enqueueSnackbar(
          t("plugins:message.installedBefore", {
            names: listOf(also),
            count: also.length,
            name: preview.name,
          }),
          { variant: "error" },
        );
      }
    }
  };

  const change = preview?.version_change ?? null; // null if not installed
  const updating = mode === "update";
  const other = !!preview?.replaces_other;
  const verb = other
    ? "install"
    : change === "newer" || (updating && !change)
      ? "update"
      : change || mode === "reinstall"
        ? "reinstall"
        : "install";
  const needs = preview?.plugin_dependencies ?? [];
  const listOf = (names) => new Intl.ListFormat(i18n.language).format(names);
  const namesIn = (state) =>
    needs.filter((need) => need.state === state).map(({ name }) => name);
  const { plugins: installedPlugins } = useInstalledPlugins();
  // An update turns on none of its needs, installed as the back's folder says
  const isInstalled =
    !!(preview?.installed_version || preview?.installed_location) ||
    installedPlugins.some(({ id }) => id === preview?.id);
  const enabling = isInstalled ? [] : namesIn("disabled");
  const stayingOff = isInstalled ? namesIn("disabled") : [];
  const installing = needs
    .filter((need) => need.state === "store" && !need.latest)
    .map(({ name }) => name);
  const older = needs.filter((need) => need.state === "store" && need.latest);
  const storePreviewOf = (need) =>
    fromStore.find((reviewed) => reviewed.need.id === need.id)?.preview ?? {};
  const previews = [
    preview,
    ...fromStore.map((reviewed) => reviewed.preview),
  ].filter(Boolean);
  const invalid = previews.find((p) => !p.is_valid);
  const needsAck = preview ? previews.some((p) => p.needs_ack) : true;
  const zipFlow = candidate?.kind !== "remote" && !fromRemote;
  const owners = zipFlow
    ? []
    : [...new Set(previews.map((p) => p.owner).filter(Boolean))];
  const author = owners.length ? listOf(owners) : null;
  // Only for a typed URL, as the parent may drop plugin while it closes
  const inStore = !!candidate?.typed && !!preview?.in_store;
  const versionKey = preview && versionNotice(preview, updating);
  const notes = [
    other &&
      t("plugins:dialog.replacesOther", {
        location: preview.installed_location,
      }),
    versionKey && t(`plugins:dialog.version.${versionKey}`),
    inStore && t("plugins:dialog.inStore"),
    preview?.removed === "critical" && t("plugins:dialog.installBlocked"),
    installing.length &&
      t("plugins:dialog.willInstall", {
        names: listOf(installing),
        count: installing.length,
      }),
    ...older.map((need) =>
      t("plugins:dialog.willInstallOlder", {
        name: need.name,
        version: need.ref.replace(/^v/, ""),
      }),
    ),
    enabling.length &&
      t("plugins:dialog.willEnable", {
        names: listOf(enabling),
        count: enabling.length,
      }),
    stayingOff.length &&
      t("plugins:dialog.staysOff", {
        names: listOf(stayingOff),
        count: stayingOff.length,
        name: preview.name,
      }),
    preview?.breaks?.length &&
      t("plugins:dialog.breaks", {
        names: listOf(preview.breaks),
        count: preview.breaks.length,
        name: preview.name,
      }),
  ].filter(Boolean);

  const titles = {
    pick: plugin
      ? t("plugins:dialog.reinstallTitle", { name: plugin.name })
      : t("plugins:dialog.pickTitle"),
    review: preview?.is_valid
      ? t(`plugins:dialog.${updating ? "update" : verb}Title`, {
          name: preview.name,
        })
      : t("plugins:dialog.reviewTitle"),
    upToDate: plugin && t("plugins:dialog.updateTitle", { name: plugin.name }),
  };
  const title =
    titles[step] ??
    (preview?.name
      ? t(`plugins:dialog.${verb}Title`, { name: preview.name })
      : plugin
        ? t(`plugins:dialog.${mode}Title`, { name: plugin.name })
        : t("plugins:dialog.pickTitle"));
  const subtitle =
    step === "working"
      ? t(`plugins:dialog.working.${verb}`)
      : zipFlow && ["pick", "loading", "review"].includes(step)
        ? t("plugins:dialog.step", { step: step === "pick" ? 1 : 2 })
        : null;

  const close = () => {
    if (step === "working") return;
    reviewing.current += 1; // a review still loading is not wanted
    forget();
    onClose();
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={close}
        fullWidth
        maxWidth="sm"
        slotProps={{ paper: { sx: { backgroundImage: "none" } } }}
      >
        <DialogTitle sx={{ pr: 6 }}>
          {title}
          {subtitle && (
            <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
              {subtitle}
            </Typography>
          )}
          <IconButton
            aria-label={t("plugins:button.close")}
            onClick={close}
            disabled={step === "working"}
            sx={{ position: "absolute", right: 12, top: 12 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent>
          {step === "pick" && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Box
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                sx={{
                  border: `1px dashed ${
                    dragging
                      ? theme.palette.primary.main
                      : theme.palette.ui.borderDark
                  }`,
                  bgcolor: dragging
                    ? alpha(theme.palette.primary.main, 0.06)
                    : "transparent",
                  borderRadius: 1,
                  p: 4,
                  textAlign: "center",
                }}
              >
                <UploadFileIcon
                  sx={{ fontSize: 32, color: "text.secondary" }}
                />
                <Typography sx={{ mt: 1 }}>
                  {t("plugins:dialog.drop")}
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    gap: 1,
                    justifyContent: "center",
                    mt: 2,
                  }}
                >
                  <Button
                    variant="outlined"
                    onClick={() => zipInput.current.click()}
                  >
                    {t("plugins:button.selectZip")}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => folderInput.current.click()}
                  >
                    {t("plugins:button.selectFolder")}
                  </Button>
                </Box>
                <input
                  ref={zipInput}
                  type="file"
                  accept=".zip"
                  hidden
                  onChange={(event) => {
                    pickZip(event.target.files[0]);
                    event.target.value = "";
                  }}
                />
                <input
                  ref={folderInput}
                  type="file"
                  hidden
                  webkitdirectory=""
                  onChange={(event) => {
                    const files = [...event.target.files].map((file) => ({
                      path: file.webkitRelativePath,
                      file,
                    }));
                    event.target.value = "";
                    pickFolder(files);
                  }}
                />
              </Box>
              {!plugin && (
                <Box
                  component="form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    review({
                      kind: "remote",
                      location: remoteUrl.trim(),
                      ref: null,
                      typed: true,
                    });
                  }}
                >
                  <Divider sx={{ mb: 2 }}>{t("plugins:dialog.or")}</Divider>
                  <Typography sx={{ fontSize: 13, mb: 1 }}>
                    {t("plugins:dialog.fromGithub")}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 1 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={remoteUrl}
                      placeholder="https://github.com/owner/repo"
                      onChange={(event) => setRemoteUrl(event.target.value)}
                    />
                    <Button
                      type="submit"
                      variant="outlined"
                      disabled={!remoteUrl.trim()}
                    >
                      {t("plugins:button.review")}
                    </Button>
                  </Box>
                </Box>
              )}
            </Box>
          )}

          {(step === "loading" || step === "working") && (
            <Box sx={{ py: 2 }}>
              <LinearProgress />
              {step === "loading" && (
                <Typography
                  sx={{ mt: 2, fontSize: 13, color: "text.secondary" }}
                >
                  {t("plugins:dialog.loading")}
                </Typography>
              )}
            </Box>
          )}

          {step === "upToDate" && <ResultBox older={change === "older"} />}

          {step === "review" && preview && (
            <Box
              data-tour="plugin-preview"
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              {zipFlow && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <InsertDriveFileOutlinedIcon
                    sx={{ fontSize: 16, color: "text.secondary" }}
                  />
                  <Typography
                    sx={{
                      fontFamily: '"Geist Mono", monospace',
                      fontSize: 12,
                      flexGrow: 1,
                    }}
                    noWrap
                  >
                    {candidate.name}
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => {
                      forget();
                      setStep("pick");
                    }}
                  >
                    {t("plugins:button.chooseOther")}
                  </Button>
                </Box>
              )}
              {!invalid ? (
                <>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 1,
                      border: `1px solid ${theme.palette.ui.border}`,
                    }}
                  >
                    <InfoRows
                      rows={[
                        {
                          label: t("plugins:detail.version"),
                          mono: true,
                          value: change
                            ? `${preview.installed_version} → ${preview.version}`
                            : preview.version,
                        },
                        ...(candidate.kind === "remote" && preview.ref
                          ? [
                              {
                                label: t("plugins:detail.release"),
                                value: (
                                  <Link
                                    href={`${candidate.location.replace(
                                      /\/$/,
                                      "",
                                    )}/releases/tag/${preview.ref}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    {t("plugins:button.viewRelease")}
                                  </Link>
                                ),
                              },
                            ]
                          : []),
                        {
                          label: t("plugins:tabs.dependencies"),
                          value: preview.dependencies.length ? (
                            <Box
                              sx={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 0.25,
                              }}
                            >
                              {preview.dependencies.map((dependency) => (
                                <span key={dependency}>{dependency}</span>
                              ))}
                            </Box>
                          ) : (
                            t("plugins:dialog.none")
                          ),
                        },
                        ...(needs.length
                          ? [
                              {
                                label: t("plugins:requires.required"),
                                value: (
                                  <Box
                                    sx={{
                                      display: "flex",
                                      flexDirection: "column",
                                      gap: 0.25,
                                    }}
                                  >
                                    {needs.map((need) => (
                                      <Box key={need.id}>
                                        {need.name}
                                        <Typography
                                          sx={{
                                            fontSize: 12,
                                            color: "text.secondary",
                                            mt: 0.25,
                                          }}
                                        >
                                          {t(
                                            `plugins:requires.state.${need.state}`,
                                          )}
                                          {need.state === "store" &&
                                            ` · ${t(trustText(storePreviewOf(need), "label"))}`}
                                        </Typography>
                                      </Box>
                                    ))}
                                  </Box>
                                ),
                              },
                            ]
                          : []),
                      ]}
                    />
                    {notes.length > 0 && (
                      <Box
                        sx={{
                          mt: 1.25,
                          pt: 1.25,
                          borderTop: `1px solid ${theme.palette.ui.border}`,
                        }}
                      >
                        {notes.map((note) => (
                          <Typography
                            key={note}
                            sx={{
                              fontSize: 13,
                              lineHeight: 1.5,
                              color: "text.secondary",
                            }}
                          >
                            {note}
                          </Typography>
                        ))}
                      </Box>
                    )}
                  </Box>
                  <TrustNotice trust={preview} before>
                    {preview.trust_tier === "local" && (
                      <Typography sx={{ fontSize: 13, mt: 1 }}>
                        {t("plugins:dialog.localWarning")}
                      </Typography>
                    )}
                    {needsAck && (
                      <FormControlLabel
                        sx={{ mt: 1 }}
                        control={
                          <Checkbox
                            size="small"
                            checked={ack}
                            onChange={(event) => setAck(event.target.checked)}
                          />
                        }
                        label={
                          <Typography sx={{ fontSize: 13 }}>
                            {author
                              ? t("plugins:dialog.ackAuthor", { author })
                              : t("plugins:dialog.ackLocal")}
                          </Typography>
                        }
                      />
                    )}
                  </TrustNotice>
                </>
              ) : (
                <ErrorBox
                  title={t("plugins:dialog.cannotInstall")}
                  error={{
                    code: "invalid_plugin",
                    detail: "",
                    params: { errors: invalid.errors },
                  }}
                />
              )}
            </Box>
          )}

          {step === "failed" && error && (
            <ErrorBox
              error={error}
              title={t(`plugins:errorTitles.${error.code}`, {
                defaultValue: t("plugins:dialog.failedTitle"),
              })}
            />
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          {step === "failed" && error?.code === "rate_limited" && (
            <Button
              variant="contained"
              onClick={() => setCredentialsOpen(true)}
            >
              {t("plugins:button.addToken")}
            </Button>
          )}
          {step === "failed" && candidate && error?.code !== "rate_limited" && (
            <Button
              onClick={() =>
                error?.code === "preview_expired" || !preview
                  ? review(candidate)
                  : setStep("review")
              }
            >
              {t("plugins:button.retry")}
            </Button>
          )}
          {step !== "working" && (
            <Button onClick={close}>
              {t(
                ["upToDate", "failed"].includes(step)
                  ? "plugins:button.close"
                  : "plugins:button.cancel",
              )}
            </Button>
          )}
          {step === "review" && (
            <Button
              data-tour="plugin-confirm"
              variant="contained"
              onClick={confirm}
              disabled={!preview || !!invalid || (needsAck && !ack)}
            >
              {t(
                `plugins:button.${updating && change === "same" ? "installRelease" : verb}`,
              )}
            </Button>
          )}
        </DialogActions>
      </Dialog>
      <CredentialsDialog
        open={credentialsOpen}
        onClose={() => setCredentialsOpen(false)}
      />
    </>
  );
}

PluginDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onDone: PropTypes.func.isRequired,
  // install a new or store plugin, update or reinstall ``plugin``
  mode: PropTypes.oneOf(["install", "update", "reinstall"]),
  plugin: PropTypes.object,
  // For update, the tag it was found at, none for GitHub's latest
  updateRef: PropTypes.string,
};
