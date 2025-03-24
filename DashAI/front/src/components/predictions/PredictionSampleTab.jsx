import React, { useEffect, useState } from "react";
import { Search } from "@mui/icons-material";
import PropTypes from "prop-types";
import { GridActionsCellItem } from "@mui/x-data-grid";
import {
  Dialog,
  Paper,
  DialogContent,
  DialogTitle,
  Grid,
  Button,
  DialogActions,
  Tabs,
  Typography,
  Tab,
  Box,
  List,
  ListItem,
  ListItemText,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import CustomLayout from "../custom/CustomLayout";
import ResultsTabInfo from "../../pages/results/components/ResultsTabInfo";
import handleCloseCustomLayout from "../../pages/results/components/ResultsTabInfo";
import { useSnackbar } from "notistack";

function PredictionSampleTab({ summary, type }) {
  const [open, setOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [error, setError] = useState(false);
  const handleCloseContent = () => {
    setOpen(false);
  };

  const columns = React.useMemo(() => {
    const commonColumns = [
      {
        field: "id",
        headerName: "Row",
        minWidth: 30,
        editable: false,
      },
    ];

    const typeSpecificColumn =
      type === "numeric"
        ? {
            field: "value",
            headerName: "Value",
            minWidth: 100,
            editable: false,
          }
        : {
            field: "value",
            headerName: "Text",
            minWidth: 500,
            editable: false,
          };

    return [...commonColumns, typeSpecificColumn];
  }, [type]);

  const rows = summary["sample_data"] || [];

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="flex-start"
      spacing={2}
    >
      <Grid item xs={12}>
        <Paper sx={{ mt: 2, height: 400 }}>
          <DataGrid rows={rows} columns={columns} disableRowSelectionOnClick />
        </Paper>
      </Grid>
    </Grid>
  );
}

export default PredictionSampleTab;
