import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  styled,
  Tooltip,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { DataGrid } from "@mui/x-data-grid";
import { formatDate, getColorByStatus } from "../../utils";
import { getPredictionStatus } from "../../utils/predictionStatus";
import { Delete } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

function PredictionsTable({ predictions, onItemClick, onItemDelete }) {
  const { t } = useTranslation(["prediction", "common"]);

  const theme = useTheme();
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
      field: "type",
      headerName: t("common:type"),
      flex: 1,
      minWidth: 150,
      renderCell: (params) => {
        const dataset = params?.row?.dataset;

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
      field: "created",
      headerName: t("common:created"),
      flex: 1.2,
      minWidth: 150,
      renderCell: (params) => formatDate(params?.row?.created),
    },
    {
      field: "duration",
      headerName: t("common:timeTaken"),
      flex: 0.8,
      minWidth: 80,
      renderCell: (params) =>
        computeDuration(params?.row?.start_time, params?.row?.end_time),
    },
    {
      field: "status",
      headerName: t("common:status"),
      flex: 1,
      minWidth: 100,
      renderCell: (params) => {
        const statusText = getPredictionStatus(params?.row?.status);
        return (
          <StyledCell color={getColorByStatus(statusText, theme)}>
            {statusText}
          </StyledCell>
        );
      },
    },
    {
      field: "delete",
      headerName: t("common:delete"),
      flex: 0.5,
      minWidth: 80,
      sortable: false,
      renderCell: (params) => (
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onItemDelete(params.row.id);
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
        <DataGrid
          rows={rows}
          columns={columns}
          disableRowSelectionOnClick
          onRowClick={(params) => onItemClick(params.row)}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 10, page: 0 },
            },
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          density="compact"
          sx={{
            fontSize: "0.75rem",
            "& .MuiDataGrid-cell": {
              fontSize: "0.75rem",
            },
            "& .MuiDataGrid-columnHeaders": {
              fontSize: "0.75rem",
            },
            "& .MuiDataGrid-row": {
              cursor: "pointer",
            },
            "& .MuiDataGrid-cell:focus": {
              outline: "none",
            },
            "& .MuiDataGrid-row:hover": {
              backgroundColor: theme.palette.ui.hover,
            },
          }}
        />
      </Paper>
    </Box>
  );
}

export default PredictionsTable;
