import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  IconButton,
  Link,
  Paper,
  Tooltip,
  Typography,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { TypeChip, VerifiedBadge } from "./PluginParts";
import {
  asVersion,
  authorLine,
  componentTypes,
  sourceOf,
} from "../pluginUtils";

function Author({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  const author = authorLine(plugin);
  const { Icon, tooltip, name } = plugin.can_update ? sourceOf(plugin) : {};
  if (!author) return null;
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        color: "text.secondary",
        minWidth: 0,
      }}
    >
      {Icon && (
        <Tooltip title={tooltip ? t(tooltip) : name}>
          <Icon sx={{ fontSize: 12 }} />
        </Tooltip>
      )}
      <Typography variant="caption" noWrap>
        {author}
      </Typography>
    </Box>
  );
}
Author.propTypes = { plugin: PropTypes.object.isRequired };

// The status mark, a span as it sits inside the card's button
function ProblemMark({ plugin }) {
  const { t } = useTranslation(["plugins"]);
  const code = plugin.problem?.code;
  let mark = null;
  if (code) {
    mark = [
      code === "blocked" ? ErrorOutlineIcon : WarningAmberIcon,
      code === "blocked" ? "error" : "warning",
      `problem.${code}.title`,
      `problem.${code}.chip`,
    ];
  } else if (plugin.removed === "critical") {
    const title = "store.notice.allowedAnyway.title"; // blocked, then allowed
    mark = [WarningAmberIcon, "warning", title, title];
  } else if (plugin.removed) {
    const title = "store.notice.removed.title";
    mark = [InfoOutlinedIcon, "default", title, title];
  }
  if (!mark) return null;
  const [Icon, color, title, label] = mark;
  return (
    <Tooltip title={t(`plugins:${title}`)}>
      <IconButton
        component="span"
        tabIndex={-1}
        size="small"
        color={color}
        aria-label={t(`plugins:${label}`)}
      >
        <Icon fontSize="small" />
      </IconButton>
    </Tooltip>
  );
}
ProblemMark.propTypes = { plugin: PropTypes.object.isRequired };

function NewVersion({ version }) {
  const { t } = useTranslation(["plugins"]);
  if (!version) return null;
  return (
    <Typography
      variant="caption"
      sx={{ color: "primary.main", whiteSpace: "nowrap", flexShrink: 0 }}
    >
      {t("plugins:label.newVersion", { version: asVersion(version) })}
    </Typography>
  );
}
NewVersion.propTypes = { version: PropTypes.string };

function Types({ plugin, sx }) {
  return (
    <Box
      sx={{ display: "flex", gap: "5px", flexWrap: "wrap", minWidth: 0, ...sx }}
    >
      {componentTypes(plugin).map((type) => (
        <TypeChip key={type} type={type} />
      ))}
    </Box>
  );
}
Types.propTypes = { plugin: PropTypes.object.isRequired, sx: PropTypes.object };

export default function PluginsCard({
  plugin,
  newVersion,
  action,
  variant = "card",
  to = null,
  tour,
}) {
  const navigate = useNavigate();
  const dim = { opacity: plugin.active ? 1 : 0.7 }; // a disabled one, still readable
  const row = variant === "row";
  const page = to ?? `/app/plugins/${plugin.id}`;

  const name = (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
      <Link
        component={RouterLink}
        to={page}
        variant="subtitle2"
        color="inherit"
        underline="none"
        noWrap
        sx={{ fontWeight: 600 }}
      >
        {plugin.name}
      </Link>
      {plugin.verified && <VerifiedBadge />}
    </Box>
  );
  const description = plugin.description && (
    <Typography
      variant="caption"
      color="text.secondary"
      noWrap={row}
      sx={
        row
          ? { minWidth: 0 }
          : {
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              mt: 1,
            }
      }
    >
      {plugin.description}
    </Typography>
  );

  return (
    <Paper
      data-tour={tour}
      elevation={0}
      onClick={(event) => {
        if (!event.target.closest("a, button")) navigate(page);
      }}
      sx={{
        width: "100%",
        p: 3,
        display: "flex",
        flexDirection: row ? "row" : "column",
        alignItems: row ? "center" : "stretch",
        justifyContent: "flex-start",
        gap: 3,
        textAlign: "left",
        cursor: "pointer",
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        transition: "border-color 0.15s, background 0.15s",
        "&:hover": { borderColor: "secondary.main" },
      }}
    >
      {row ? (
        <>
          <Box sx={{ width: 280, flexShrink: 0, minWidth: 0, ...dim }}>
            {name}
            <Author plugin={plugin} />
          </Box>
          <Box sx={{ display: "flex", flex: 1, minWidth: 0, ...dim }}>
            {description}
          </Box>
          <NewVersion version={newVersion} />
          <Types
            plugin={plugin}
            sx={{ maxWidth: 360, justifyContent: "flex-end", ...dim }}
          />
          {action}
          <Box sx={dim}>
            <ProblemMark plugin={plugin} />
          </Box>
        </>
      ) : (
        <>
          <Box
            sx={{ display: "flex", gap: 3, alignItems: "flex-start", ...dim }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              {name}
              <Author plugin={plugin} />
              {description}
            </Box>
            <ProblemMark plugin={plugin} />
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          <Box sx={{ display: "flex", alignItems: "flex-end", gap: 2 }}>
            <Types plugin={plugin} sx={{ flex: 1, ...dim }} />
            <NewVersion version={newVersion} />
            {action}
          </Box>
        </>
      )}
    </Paper>
  );
}

PluginsCard.propTypes = {
  plugin: PropTypes.object.isRequired,
  newVersion: PropTypes.string,
  action: PropTypes.node, // a button in its footer
  variant: PropTypes.oneOf(["card", "row"]),
  tour: PropTypes.string,
  to: PropTypes.string, // its page, by default /app/plugins/<id>
};
