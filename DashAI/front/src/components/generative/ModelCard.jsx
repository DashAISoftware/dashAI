import { useEffect, useRef, useState } from "react";
import { Box, Paper, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { useTranslation } from "react-i18next";

const DESCRIPTION_LINE_CLAMP = 3;

export default function ModelCard({
  model,
  color,
  isSelected,
  onClick,
  dataTour,
}) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const { t } = useTranslation(["generative"]);
  const descRef = useRef(null);

  useEffect(() => {
    const el = descRef.current;
    if (el) {
      setIsClamped(el.scrollHeight > el.clientHeight + 1);
    }
  }, [model.description]);

  const handleToggleExpand = (e) => {
    e.stopPropagation();
    setExpanded((prev) => !prev);
  };

  return (
    <Paper
      data-tour={dataTour}
      elevation={isSelected ? 3 : 1}
      onClick={onClick}
      sx={{
        p: 2,
        cursor: "pointer",
        borderLeft: `4px solid ${color}`,
        outline: isSelected
          ? `2px solid ${color}`
          : `1px solid ${theme.palette.divider}`,
        outlineOffset: "-1px",
        bgcolor: isSelected
          ? alpha(color, 0.06)
          : theme.palette.background.paper,
        transition: "background-color 0.15s ease, box-shadow 0.15s ease",
        "&:hover": {
          bgcolor: alpha(color, 0.08),
          boxShadow: theme.shadows[3],
        },
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          mb: 0.5,
        }}
      >
        <Typography
          variant="subtitle1"
          fontWeight="bold"
          sx={{ color: isSelected ? color : "text.primary", lineHeight: 1.3 }}
        >
          {model.display_name ? model.display_name : model.name}
        </Typography>
        {isSelected && (
          <CheckCircleIcon sx={{ color, ml: 1, flexShrink: 0, fontSize: 20 }} />
        )}
      </Box>

      <Typography
        ref={descRef}
        variant="body2"
        color="text.secondary"
        sx={{
          mt: 0.5,
          lineHeight: 1.5,
          ...(!expanded && {
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: DESCRIPTION_LINE_CLAMP,
            WebkitBoxOrient: "vertical",
          }),
        }}
      >
        {model.description
          ? model.description
          : t("generative:label.noDescriptionAvailable")}
      </Typography>

      {(isClamped || expanded) && (
        <Typography
          variant="caption"
          onClick={handleToggleExpand}
          sx={{
            mt: 0.5,
            color,
            fontWeight: 600,
            cursor: "pointer",
            alignSelf: "flex-start",
            "&:hover": { textDecoration: "underline" },
          }}
        >
          {expanded
            ? t("generative:label.showLess")
            : t("generative:label.readMore")}
        </Typography>
      )}
    </Paper>
  );
}
