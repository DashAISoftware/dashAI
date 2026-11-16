import React, { useState } from "react";
import PropTypes from "prop-types";
import { Box, IconButton, Link, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import CheckIcon from "@mui/icons-material/Check";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useInstalledPlugins, useStore } from "../../../hooks/usePlugins";
import { InfoRows, SectionLabel, TypeChip, filledRows } from "./PluginParts";
import {
  asVersion,
  dependentsOf,
  fileName,
  formatDate,
  shortUrl,
  splitRequirement,
  trustOf,
  trustText,
} from "../pluginUtils";

const mono = { fontFamily: '"Geist Mono", monospace', fontSize: 12 };
const oneLine = {
  display: "block",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

function Item({ name, nameSx, children }) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 1.5,
        py: 0.75,
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontSize: 13, ...nameSx }} title={name}>
          {name}
        </Typography>
      </Box>
      <Box sx={{ flexShrink: 0 }}>{children}</Box>
    </Box>
  );
}
Item.propTypes = {
  name: PropTypes.string.isRequired,
  nameSx: PropTypes.object,
  children: PropTypes.node,
};

export default function DetailPanel({ children }) {
  const theme = useTheme();
  return (
    <Box
      component="aside"
      data-tour="plugin-detail-panel"
      sx={{
        alignSelf: "start",
        p: 4,
        borderRadius: 1,
        border: `1px solid ${theme.palette.ui.border}`,
        bgcolor: "background.box",
        "& > section": { py: 2.5 },
        "& > section:first-of-type": { pt: 0 },
        "& > section:last-of-type": { pb: 0 },
        "& > section + section": {
          borderTop: `1px solid ${theme.palette.ui.border}`,
        },
        "& > section dl": { rowGap: 1.25 },
      }}
    >
      {children}
    </Box>
  );
}
DetailPanel.propTypes = { children: PropTypes.node };

const SHOWN_ITEMS = 2;

function Capped({ children }) {
  const { t } = useTranslation(["plugins"]);
  const [all, setAll] = useState(false);
  const items = React.Children.toArray(children);
  if (items.length <= SHOWN_ITEMS) return items;
  return (
    <>
      {all ? items : items.slice(0, SHOWN_ITEMS)}
      <Link
        component="button"
        onClick={() => setAll(!all)}
        sx={{ fontSize: 12, mt: 1 }}
      >
        {t(all ? "plugins:button.showLess" : "plugins:button.showMore")}
      </Link>
    </>
  );
}
Capped.propTypes = { children: PropTypes.node };

function Section({ title, tour, children }) {
  return (
    <section data-tour={tour}>
      <SectionLabel sx={{ mb: 1.5 }}>{title}</SectionLabel>
      {children}
    </section>
  );
}
Section.propTypes = {
  title: PropTypes.string,
  tour: PropTypes.string,
  children: PropTypes.node,
};

export function TrustSection({ plugin, before = false }) {
  const { t } = useTranslation(["plugins"]);
  const { Icon, color } = trustOf(plugin.trust_tier);
  return (
    <Section title={t("plugins:detail.trustLevel")} tour="plugin-detail-trust">
      <Box
        component="span"
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.75,
          px: 1.25,
          py: 0.625,
          borderRadius: "3px",
          border: `1px solid ${alpha(color, 0.45)}`,
          bgcolor: alpha(color, 0.08),
          color,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        <Icon sx={{ fontSize: 16 }} />
        {t(trustText(plugin, "label"))}
      </Box>
      <Typography
        sx={{
          mt: 1.25,
          fontSize: 12,
          lineHeight: 1.6,
          color: "text.secondary",
        }}
      >
        {t(trustText(plugin, before ? "textBefore" : "text"))}
      </Typography>
    </Section>
  );
}
TrustSection.propTypes = {
  plugin: PropTypes.object.isRequired,
  before: PropTypes.bool,
};

function Sha({ value }) {
  const { t } = useTranslation(["common"]);
  const [copied, setCopied] = useState(false);
  const copy = () =>
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  const Icon = copied ? CheckIcon : ContentCopyIcon;
  return (
    <Box component="span" sx={{ display: "inline-flex", gap: 1.5 }}>
      <span title={value}>{value.slice(0, 16)}…</span>
      <IconButton
        aria-label={t("common:copy")}
        title={t("common:copy")}
        onClick={copy}
        sx={{ p: 0, color: "text.secondary" }}
      >
        <Icon sx={{ fontSize: 14 }} />
      </IconButton>
    </Box>
  );
}
Sha.propTypes = { value: PropTypes.string.isRequired };

// What is on disk when installed, else the release the store offers
export function InstallationSection({ plugin, license }) {
  const { t, i18n } = useTranslation(["plugins"]);
  const [more, setMore] = useState(false);
  const git = !!plugin.can_update;
  const version = asVersion(plugin.version);
  const installed = formatDate(plugin.installed_at, i18n.language);
  const updated = formatDate(plugin.updated_at, i18n.language);
  const file = git ? plugin.asset : plugin.location;
  const name = git ? file : fileName(file);
  const fileRow = {
    label: t("plugins:detail.file"),
    value: file && (
      <Box component="span" title={file} sx={oneLine}>
        {name}
      </Box>
    ),
    mono: git,
  };
  const link = (href, text, sx) => (
    <Link href={href} target="_blank" rel="noopener noreferrer" sx={sx}>
      {text}
    </Link>
  );
  const rows = filledRows([
    { label: t("plugins:detail.version"), value: version, mono: true },
    plugin.fromStore
      ? {
          label: t("plugins:store.published"),
          value: formatDate(plugin.published_at, i18n.language),
        }
      : { label: t("plugins:detail.installedAt"), value: installed },
    {
      label: t("plugins:detail.updatedAt"),
      value: !plugin.fromStore && updated !== installed ? updated : null,
    },
    git
      ? {
          label: t("plugins:detail.repository"),
          value: link(plugin.web_url, shortUrl(plugin.web_url), mono),
        }
      : fileRow,
    {
      label: t("plugins:detail.license"),
      value:
        license &&
        link(
          `https://spdx.org/licenses/${encodeURIComponent(license)}.html`,
          license,
        ),
    },
  ]);
  const extra = filledRows([
    { label: t("plugins:detail.id"), value: plugin.id, mono: true },
    {
      label: t("plugins:detail.tag"),
      value: plugin.ref !== version ? plugin.ref : null,
      mono: true,
    },
    ...(git ? [fileRow] : []),
    {
      label: t("plugins:detail.path"),
      value: !git && name !== file ? file : null,
      mono: true,
    },
    {
      label: "Commit",
      value: git ? plugin.commit?.slice(0, 10) : null,
      mono: true,
    },
    {
      label: "SHA-256",
      value: plugin.sha256 && <Sha value={plugin.sha256} />,
      mono: true,
    },
    {
      label: t("plugins:detail.signedBy"),
      value: plugin.trust_tier === "attested" ? plugin.workflow : null,
      mono: true,
    },
  ]);
  return (
    <Section
      title={t(
        plugin.fromStore
          ? "plugins:detail.release"
          : "plugins:detail.installation",
      )}
    >
      <InfoRows rows={more ? [...rows, ...extra] : rows} />
      <Link
        component="button"
        onClick={() => setMore(!more)}
        sx={{ fontSize: 12, mt: 1.5 }}
      >
        {t(more ? "plugins:button.hideDetails" : "plugins:button.showDetails")}
      </Link>
    </Section>
  );
}
InstallationSection.propTypes = {
  plugin: PropTypes.object.isRequired,
  license: PropTypes.string,
};

export function ComponentsSection({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  if (!plugin.components.length) return null;
  return (
    <Section
      title={`${t("plugins:tabs.components")} · ${plugin.components.length}`}
    >
      <Capped>
        {plugin.components.map((name, index) => (
          <Item key={name} name={name}>
            <TypeChip type={plugin.component_types[index] ?? ""} />
          </Item>
        ))}
      </Capped>
    </Section>
  );
}
ComponentsSection.propTypes = { plugin: PropTypes.object.isRequired };

export function DependenciesSection({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  if (!plugin.dependencies.length) return null;
  return (
    <Section
      title={`${t("plugins:tabs.dependencies")} · ${plugin.dependencies.length}`}
    >
      <Capped>
        {plugin.dependencies.map((requirement) => {
          const [name, specifier] = splitRequirement(requirement);
          return (
            <Item key={requirement} name={name} nameSx={mono}>
              <Typography sx={{ ...mono, color: "text.secondary" }}>
                {specifier}
              </Typography>
            </Item>
          );
        })}
      </Capped>
    </Section>
  );
}
DependenciesSection.propTypes = { plugin: PropTypes.object.isRequired };

const wrapName = { fontSize: 13, minWidth: 0, overflowWrap: "anywhere" };

function PluginsSection({ title, items }) {
  const { t } = useTranslation(["plugins"]);
  if (!items.length) return null;
  return (
    <Section title={`${title} · ${items.length}`}>
      <Capped>
        {items.map(({ id, name, state, spec, linked }) => (
          <Box key={id} sx={{ py: 0.75 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: 1.5,
              }}
            >
              {linked ? (
                <Link
                  component={RouterLink}
                  to={`/app/plugins/${id}`}
                  sx={wrapName}
                >
                  {name}
                </Link>
              ) : (
                <Typography sx={wrapName}>{name}</Typography>
              )}
              {spec && (
                <Typography
                  sx={{ ...mono, flexShrink: 0, color: "text.secondary" }}
                >
                  {spec}
                </Typography>
              )}
            </Box>
            {state && (
              <Typography
                sx={{ fontSize: 12, color: "text.secondary", mt: 0.25 }}
              >
                {t(`plugins:requires.state.${state}`)}
              </Typography>
            )}
          </Box>
        ))}
      </Capped>
    </Section>
  );
}
PluginsSection.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.array.isRequired,
};

export function RequiresSections({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  const { plugins } = useInstalledPlugins();
  const { store } = useStore();
  const wrong = plugin.fromStore
    ? store?.wrong_versions?.[plugin.id]
    : plugin.problem?.params?.ids;
  const required = (plugin.plugin_dependencies || []).map((id) => {
    const installed = plugins.find((p) => p.id === id);
    const listed = store?.plugins.find((entry) => entry.id === id);
    let state = installed
      ? "installed"
      : !listed
        ? "unlisted"
        : !listed.offered
          ? "incompatible"
          : "uninstalled";
    if (installed && !plugin.fromStore) {
      state = installed.active
        ? "active"
        : installed.enabled || installed.problem
          ? "problem"
          : "disabled";
    }
    if (wrong?.includes(id)) state = installed ? "version" : "incompatible";
    return {
      id,
      name: installed?.name ?? listed?.name ?? id,
      state,
      spec: plugin.plugin_specifiers?.[id],
      linked: Boolean(installed || listed),
    };
  });
  return (
    <>
      <PluginsSection title={t("plugins:requires.required")} items={required} />
      {!plugin.fromStore && (
        <PluginsSection
          title={t("plugins:requires.dependents")}
          items={dependentsOf(plugins, plugin.id).map(({ id, name }) => ({
            id,
            name,
            linked: true,
          }))}
        />
      )}
    </>
  );
}
RequiresSections.propTypes = { plugin: PropTypes.object.isRequired };

export function AuthorSection({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  const { authors } = plugin;
  // A lone name says no more than the card's byline.
  if (
    !authors.length ||
    (authors.length === 1 && !authors[0].url && !authors[0].email)
  )
    return null;
  return (
    <Section
      title={t(
        authors.length > 1 ? "plugins:detail.authors" : "plugins:detail.author",
      )}
    >
      <Capped>
        {authors.map((author, index) => (
          <Box key={index} sx={{ py: 0.75 }}>
            {author.url ? (
              <Link
                href={author.url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.75,
                  fontSize: 13,
                  py: 0.5,
                }}
              >
                {author.name || shortUrl(author.url)}
                <OpenInNewIcon sx={{ fontSize: 14 }} />
              </Link>
            ) : (
              <Typography sx={{ fontSize: 13 }}>{author.name}</Typography>
            )}
            {author.email && (
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                {author.email}
              </Typography>
            )}
          </Box>
        ))}
      </Capped>
    </Section>
  );
}
AuthorSection.propTypes = { plugin: PropTypes.object.isRequired };
