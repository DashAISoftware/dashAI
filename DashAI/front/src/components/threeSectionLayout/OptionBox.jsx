import { Box, Typography, Button, useTheme } from "@mui/material";

const EMPTY_ARRAY = [];

export default function OptionBox({
  optionName,
  description,
  onClick,
  Icon = null,
  tag = null,
  chips = EMPTY_ARRAY,
  dataTour,
  ...otherProps
}) {
  const theme = useTheme();
  const accent = theme.palette.primary.main;
  const accentDim = theme.palette.primary.lighter || theme.palette.action.hover;
  const accentBorder = theme.palette.primary.light;
  const accentGlow =
    theme.palette.mode === "dark"
      ? "rgba(33, 150, 243, 0.08)"
      : "rgba(33, 150, 243, 0.06)";

  return (
    <Button
      data-tour={dataTour}
      onClick={onClick}
      sx={{
        p: 0,
        width: "100%",
        height: "100%",
        textAlign: "left",
        textTransform: "none",
        borderRadius: "4px",
      }}
      {...otherProps}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
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
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            mb: "14px",
          }}
        >
          {Icon && (
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
          )}

          {tag && (
            <Box sx={{ textAlign: "right" }}>
              <Box
                sx={{
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
          )}
        </Box>

        <Typography
          sx={{
            fontSize: "19px",
            fontWeight: 600,
            color: theme.palette.text.primary,
            letterSpacing: "-0.01em",
            mb: "5px",
          }}
        >
          {optionName}
        </Typography>

        <Typography
          variant="body2"
          component="p"
          sx={{
            fontSize: "16px",
            fontWeight: 300,
            color: theme.palette.text.secondary,
            lineHeight: 1.65,
            flexGrow: 1,
          }}
        >
          {description}
        </Typography>

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
              fontSize: "18px",
              color: theme.palette.text.disabled,
              transition: "color 0.15s, transform 0.15s",
              flexShrink: 0,
              ml: 1,
            }}
          >
            {"->"}
          </Box>
        </Box>
      </Box>
    </Button>
  );
}
