import { useRef, useCallback, useState } from "react";
import {
  Card,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import BarChartOutlinedIcon from "@mui/icons-material/BarChartOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import DataObjectOutlinedIcon from "@mui/icons-material/DataObjectOutlined";
import html2canvas from "html2canvas";
import { useTranslation } from "react-i18next";

/**
 * @param {Object} props
 * @param {string} props.filename - Base filename for exports
 * @param {Array|Object} props.exportData - Data for CSV/JSON export (optional)
 */
export default function ExportableCard({
  children,
  filename = "export",
  exportData,
  sx,
  ...props
}) {
  const ref = useRef(null);
  const { t } = useTranslation(["datasets"]);
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (e) => {
    e.stopPropagation();
    setAnchorEl(e.currentTarget);
  };

  const handleClose = () => setAnchorEl(null);

  const captureElement = useCallback(
    async (element) => {
      if (!element) return;
      const canvas = await html2canvas(element, {
        backgroundColor: null,
        scale: 2,
      });
      const link = document.createElement("a");
      link.download = `${filename}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    },
    [filename],
  );

  const handleExportCard = useCallback(async () => {
    handleClose();
    await captureElement(ref.current);
  }, [captureElement]);

  const handleExportChart = useCallback(async () => {
    handleClose();
    if (!ref.current) return;
    const chart =
      ref.current.querySelector(".recharts-wrapper") ||
      ref.current.querySelector(".js-plotly-plot");
    if (chart) {
      const canvas = await html2canvas(chart, {
        backgroundColor: null,
        scale: 2,
      });
      const link = document.createElement("a");
      link.download = `${filename}_chart.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    }
  }, [filename]);

  const handleExportCSV = useCallback(() => {
    handleClose();
    if (!exportData) return;
    const data = Array.isArray(exportData) ? exportData : [exportData];
    if (data.length === 0) return;
    const headers = Object.keys(data[0]);
    const csvRows = [
      headers.join(","),
      ...data.map((row) =>
        headers
          .map((h) => {
            const val = row[h] ?? "";
            const str = String(val);
            return str.includes(",") || str.includes('"') || str.includes("\n")
              ? `"${str.replace(/"/g, '""')}"`
              : str;
          })
          .join(","),
      ),
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [exportData, filename]);

  const handleExportJSON = useCallback(() => {
    handleClose();
    if (!exportData) return;
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [exportData, filename]);

  const hasChart = true; // Charts are detected at runtime
  const hasData = Boolean(exportData);

  return (
    <Card ref={ref} sx={{ position: "relative", ...sx }} {...props}>
      <Tooltip title={t("datasets:label.exportImage")} arrow>
        <IconButton
          size="small"
          onClick={handleClick}
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            zIndex: 1,
            color: "primary.main",
            opacity: 1,
          }}
        >
          <FileDownloadOutlinedIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: { minWidth: 200 },
          },
        }}
      >
        <MenuItem onClick={handleExportCard}>
          <ListItemIcon>
            <ImageOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t("datasets:label.exportCardImage")}</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleExportChart}>
          <ListItemIcon>
            <BarChartOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t("datasets:label.exportChartImage")}</ListItemText>
        </MenuItem>

        {hasData && (
          <MenuItem onClick={handleExportCSV}>
            <ListItemIcon>
              <TableChartOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>{t("datasets:label.exportCSV")}</ListItemText>
          </MenuItem>
        )}

        {hasData && (
          <MenuItem onClick={handleExportJSON}>
            <ListItemIcon>
              <DataObjectOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>{t("datasets:label.exportJSON")}</ListItemText>
          </MenuItem>
        )}
      </Menu>

      {children}
    </Card>
  );
}
