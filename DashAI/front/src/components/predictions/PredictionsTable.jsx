import React from "react";
import {
  Box,
  Typography,
  Paper,
  styled,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTranslation } from "react-i18next";
import { formatDate, getColorByStatus } from "../../utils";
import { getPredictionStatus } from "../../utils/predictionStatus";
import { Delete } from "@mui/icons-material";

function PredictionsTable({ predictions, onItemClick, onItemDelete }) {
  const { t, i18n } = useTranslation(["prediction", "common"]);

  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const StyledCell = styled("div")(({ theme, color }) => ({
    display: "inline-block",
    padding: theme.spacing(0.5),
    borderRadius: theme.shape.borderRadius,
    backgroundColor: color,
  }));

  const computeDuration = (start, end) => {
    if (!start || !end) return "-";

    const startTime = new Date(start);
    const endTime = end ? new Date(end) : new Date();
    const diffMs = endTime - startTime;

    if (diffMs < 0) return "-";

    const seconds = Math.floor(diffMs / 1000);
    return `${seconds}s`;
  };

  const columns = [
    {
      accessorKey: "type",
      header: t("common:type"),
      grow: 1,
      minSize: 150,
      Cell: ({ row }) => {
        const dataset = row.original?.dataset;

        return dataset ? (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              height: "100%",
              overflow: "hidden",
              fontSize: "0.75rem",
            }}
          >
            <Typography
              variant="body2"
              fontWeight={500}
              sx={{ lineHeight: 1.1, fontSize: "inherit" }}
            >
              {t("common:dataset")}
            </Typography>

            <Typography
              variant="caption"
              noWrap
              sx={{
                color: theme.palette.text.secondary,
                lineHeight: 1.1,
                mt: 0.2,
                fontSize: "95%",
              }}
            >
              {dataset.name}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              height: "100%",
            }}
          >
            <Typography
              variant="body2"
              fontWeight={600}
              sx={{ lineHeight: 1.1, fontSize: "0.75rem" }}
            >
              {t("prediction:label.manualInput")}
            </Typography>
          </Box>
        );
      },
    },
    {
      accessorKey: "created",
      header: t("common:created"),
      grow: 1.2,
      minSize: 150,
      Cell: ({ row }) => formatDate(row.original?.created),
    },
    {
      id: "duration",
      header: t("common:timeTaken"),
      grow: 0.8,
      minSize: 80,
      Cell: ({ row }) =>
        computeDuration(row.original?.start_time, row.original?.end_time),
    },
    {
      accessorKey: "status",
      header: t("common:status"),
      grow: 1,
      minSize: 100,
      Cell: ({ row }) => {
        const statusText = getPredictionStatus(row.original?.status);
        return (
          <StyledCell color={getColorByStatus(statusText, theme)}>
            {statusText}
          </StyledCell>
        );
      },
    },
    {
      id: "delete",
      header: t("common:delete"),
      grow: 0.5,
      minSize: 80,
      enableSorting: false,
      enableColumnFilter: false,
      Cell: ({ row }) => (
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onItemDelete(row.original.id);
          }}
        >
          <Delete fontSize="small" color="error" />
        </IconButton>
      ),
    },
  ];

  if (!predictions || predictions.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography sx={{ color: theme.palette.text.secondary }}>
          {t("prediction:label.noPredictionsYet")}
        </Typography>
        <Typography
          variant="caption"
          sx={{ color: theme.palette.text.secondary }}
        >
          {t("prediction:label.runFirstPrediction")}
        </Typography>
      </Box>
    );
  }

  const rows = predictions.map((prediction) => ({
    id: prediction.id,
    ...prediction,
  }));

  const table = useMaterialReactTable({
    columns,
    data: rows,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: { density: "compact" },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => onItemClick(row.original),
      sx: { cursor: "pointer" },
    }),
    enableRowSelection: false,
  });

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
        {t("prediction:label.predictions")}
      </Typography>
      <Typography
        variant="body2"
        sx={{ color: theme.palette.text.secondary, mb: 2 }}
      >
        {t("prediction:label.clickToViewOrDelete")}
      </Typography>
      <Paper sx={{ width: "100%" }}>
        <MaterialReactTable table={table} />
      </Paper>
    </Box>
  );
}

export default PredictionsTable;
