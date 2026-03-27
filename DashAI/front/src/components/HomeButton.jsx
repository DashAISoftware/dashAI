import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";
import { useTheme } from "@mui/material/styles";

function HomeButton({
  title,
  description,
  to,
  Icon,
  accent,
  accentDim,
  accentBorder,
  accentGlow,
  tag,
  chips,
}) {
  const theme = useTheme();

  return (
    <Box
      component={RouterLink}
      to={to}
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: theme.palette.background.paper,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: "4px",
        padding: "22px 24px",
        textDecoration: "none",
        cursor: "pointer",
        position: "relative",
        overflow: "hidden",
        transition: "border-color 0.2s, background 0.2s, transform 0.15s",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: "10%",
          right: "10%",
          height: "1px",
          background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
          opacity: 0,
          transition: "opacity 0.25s",
        },
        "&:hover": {
          transform: "translateY(-1px)",
          borderColor: accentBorder,
          background: accentGlow,
        },
        "&:hover::before": {
          opacity: 1,
        },
        "&:hover .card-arrow": {
          transform: "translateX(3px)",
          color: accent,
        },
      }}
    >
      {/* Header: icon + tag */}
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          mb: "14px",
        }}
      >
        <Box
          sx={{
            width: 38,
            height: 38,
            borderRadius: "6px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: accentDim,
            color: accent,
            flexShrink: 0,
          }}
        >
          <Icon sx={{ fontSize: 25 }} />
        </Box>
        <Box sx={{ textAlign: "right" }}>
          <Box
            sx={{
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: "12.5px",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              px: "8px",
              py: "3px",
              borderRadius: "2px",
              border: `1px solid ${accentBorder}`,
              background: accentDim,
              color: accent,
              display: "inline-block",
            }}
          >
            {tag}
          </Box>
        </Box>
      </Box>

      {/* Title */}
      <Typography
        sx={{
          fontFamily: '"IBM Plex Sans", sans-serif',
          fontSize: "19px",
          fontWeight: 600,
          color: theme.palette.text.primary,
          letterSpacing: "-0.01em",
          mb: "5px",
        }}
      >
        {title}
      </Typography>

      {/* Description */}
      <Typography
        sx={{
          fontFamily: '"IBM Plex Sans", sans-serif',
          fontSize: "16px",
          fontWeight: 300,
          color: theme.palette.text.secondary,
          lineHeight: 1.65,
          flexGrow: 1,
        }}
      >
        {description}
      </Typography>

      {/* Footer: chips + arrow */}
      <Box
        sx={{
          mt: "16px",
          pt: "14px",
          borderTop: `1px solid ${theme.palette.ui.borderLight}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
          {chips.map((chip) => (
            <Box
              key={chip}
              sx={{
                fontFamily: '"IBM Plex Mono", monospace',
                fontSize: "12.5px",
                letterSpacing: "0.06em",
                border: `1px solid ${theme.palette.divider}`,
                color: theme.palette.text.disabled,
                px: "7px",
                py: "2px",
                borderRadius: "2px",
                background: theme.palette.background.default,
              }}
            >
              {chip}
            </Box>
          ))}
        </Box>
        <Box
          className="card-arrow"
          sx={{
            fontFamily: '"IBM Plex Mono", monospace',
            fontSize: "18px",
            color: theme.palette.text.disabled,
            transition: "color 0.15s, transform 0.15s",
            flexShrink: 0,
            ml: 1,
          }}
        >
          →
        </Box>
      </Box>
    </Box>
  );
}

HomeButton.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  to: PropTypes.string.isRequired,
  Icon: PropTypes.elementType.isRequired,
  accent: PropTypes.string.isRequired,
  accentDim: PropTypes.string.isRequired,
  accentBorder: PropTypes.string.isRequired,
  accentGlow: PropTypes.string.isRequired,
  tag: PropTypes.string.isRequired,
  chips: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default HomeButton;
