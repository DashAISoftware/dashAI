import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { useHardwareMonitor } from "../../hooks/useHardwareMonitor";
import HardwareMonitorPanel from "./HardwareMonitorPanel";

export default function HardwareMonitorButton() {
  const theme = useTheme();
  const { t } = useTranslation(["common"]);
  const [anchorEl, setAnchorEl] = useState(null);

  const open = Boolean(anchorEl);
  const { stats, connected } = useHardwareMonitor(open);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <Tooltip title={t("common:hardwareMonitor.title")}>
        <IconButton
          onClick={handleClick}
          aria-label={t("common:hardwareMonitor.title")}
          sx={{
            width: 28,
            height: 28,
            borderRadius: "4px",
            border: `1px solid ${theme.palette.divider}`,
            color: theme.palette.text.secondary,
            "&:hover": {
              background: theme.palette.ui.hover,
              color: theme.palette.text.primary,
            },
          }}
        >
          <MonitorHeartIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Tooltip>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
      >
        <HardwareMonitorPanel stats={stats} connected={connected} />
      </Popover>
    </>
  );
}
