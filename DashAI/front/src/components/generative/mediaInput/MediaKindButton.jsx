import { IconButton, Tooltip } from "@mui/material";

export function MediaKindButton({
  icon: Icon,
  tooltip,
  disabled,
  onClick,
  tooltipPlacement = "top",
}) {
  return (
    <Tooltip title={tooltip} placement={tooltipPlacement} arrow>
      <span>
        <IconButton
          onClick={onClick}
          disabled={disabled}
          sx={(theme) => {
            const isDark = theme.palette.mode === "dark";
            const bg = isDark
              ? theme.palette.grey[700]
              : theme.palette.grey[200];
            const fg = isDark
              ? theme.palette.grey[100]
              : theme.palette.grey[800];
            const disabledBg =
              theme.palette.ui?.disabled ??
              theme.palette.action.disabledBackground;
            const borderColor =
              theme.palette.ui?.border ?? theme.palette.divider;
            return {
              width: 40,
              height: 40,
              borderRadius: 1,
              color: fg,
              backgroundColor: bg,
              "&:hover": { backgroundColor: bg },
              "&.Mui-disabled": {
                position: "relative",
                overflow: "hidden",
                color: theme.palette.text.disabled,
                backgroundColor: disabledBg,
                border: `1px solid ${borderColor}`,
                opacity: 0.6,
                filter: "grayscale(0.6)",
                cursor: "not-allowed",
              },
              "&.Mui-disabled::after": {
                content: '""',
                position: "absolute",
                inset: 0,
                borderRadius: 1,
                pointerEvents: "none",
                background:
                  "repeating-linear-gradient(45deg, transparent, transparent 6px, rgba(0,0,0,0.12) 6px, rgba(0,0,0,0.12) 12px)",
              },
            };
          }}
        >
          <Icon fontSize="small" />
        </IconButton>
      </span>
    </Tooltip>
  );
}
