import {
  Box,
  Chip,
  List,
  ListItemButton,
  ListItemText,
  Typography,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

const STATUS_COLOR = {
  published: "success",
  error: "error",
};

/**
 * Right panel of the export progress step: every export of the dataset.
 *
 * @param {string} datasetName - Name of the exported dataset.
 * @param {Array<object>} exports - The dataset's export records, newest first.
 * @param {number} currentId - Export shown in the center, highlighted here.
 * @param {function} platformLabel - Maps an exporter name to its label.
 * @param {function} onSelect - Opens the clicked export.
 */
export default function ExportHistoryPanel({
  datasetName,
  exports,
  currentId,
  platformLabel,
  onSelect,
}) {
  const { t, i18n } = useTranslation(["export"]);
  const theme = useTheme();

  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          height: 64,
          display: "flex",
          alignItems: "center",
        }}
      >
        <Typography variant="h6" color="text.primary" noWrap>
          {t("export:historyTitle", { dataset: datasetName })}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, overflowY: "auto", px: 2, py: 2 }}>
        {exports.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
            {t("export:historyEmpty")}
          </Typography>
        ) : (
          <List disablePadding>
            {exports.map((row) => (
              <ListItemButton
                key={row.id}
                selected={row.id === currentId}
                onClick={() => onSelect(row)}
                sx={{ borderRadius: 1, alignItems: "flex-start" }}
              >
                <ListItemText
                  primary={
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 1,
                      }}
                    >
                      <span>
                        {platformLabel(row.exporter_name)}
                        {row.remote_id ? ` · ID ${row.remote_id}` : ""}
                      </span>
                      <Chip
                        size="small"
                        variant="outlined"
                        color={STATUS_COLOR[row.status] ?? "default"}
                        label={t(`export:status.${row.status}`)}
                      />
                    </Box>
                  }
                  secondary={
                    row.created
                      ? new Date(row.created).toLocaleString(i18n.language)
                      : null
                  }
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>
    </SideBar>
  );
}

ExportHistoryPanel.propTypes = {
  datasetName: PropTypes.string.isRequired,
  exports: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      exporter_name: PropTypes.string.isRequired,
      status: PropTypes.string.isRequired,
      remote_id: PropTypes.string,
      created: PropTypes.string,
    }),
  ).isRequired,
  currentId: PropTypes.number,
  platformLabel: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};
