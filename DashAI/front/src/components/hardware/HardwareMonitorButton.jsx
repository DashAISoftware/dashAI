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
            ml: 1,
            color:
              theme.palette.mode === "dark"
                ? "inherit"
                : theme.palette.text.primary,
          }}
        >
          <MonitorHeartIcon />
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
