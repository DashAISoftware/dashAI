import { Box, Typography, ButtonBase, useTheme } from "@mui/material";

export default function OptionBox({
  optionName,
  description,
  onClick,
  Icon = null,
  chips = [],
  dataTour,
  ...otherProps
}) {
  const theme = useTheme();
  const accent = theme.palette.accent.amber;
  const accentDim = theme.palette.accent.amberDim;
  const accentBorder = theme.palette.accent.amberBorder;
  const accentGlow = theme.palette.accent.amberGlow;

  return (
    <ButtonBase
      data-tour={dataTour}
      onClick={onClick}
      sx={{
        width: "100%",
        height: "100%",
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        background: theme.palette.background.paper,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: "4px",
        padding: "22px 24px",
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
      {...otherProps}
    >
      {/* Header: icon */}
      {Icon && (
        <Box sx={{ display: "flex", mb: "14px", width: "100%" }}>
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
        </Box>
      )}

      {/* Title */}
      <Typography
        sx={{
          ...theme.typography.cardTitle,
          color: theme.palette.text.primary,
          mb: "5px",
          width: "100%",
        }}
      >
        {optionName}
      </Typography>

      {/* Description */}
      <Typography
        sx={{
          fontSize: "15px",
          fontWeight: 300,
          color: theme.palette.text.secondary,
          lineHeight: 1.65,
          flexGrow: 1,
          width: "100%",
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
          width: "100%",
        }}
      >
        <Box sx={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
          {chips.map((chip) => (
            <Box
              key={chip}
              sx={{
                ...theme.typography.statusBadge,
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
    </ButtonBase>
  );
}
