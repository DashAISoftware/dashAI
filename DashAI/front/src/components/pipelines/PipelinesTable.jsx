import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Button,
  Grid,
  Paper,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
} from "@mui/icons-material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { getPipelines, deletePipeline } from "../../api/pipeline";
import { formatDate } from "../../utils";
import { Visibility as ViewIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import DeleteItemModal from "../../components/custom/DeleteItemModal";

function PipelinesTable({
  handleOpenNewPipeline,
  updateTableFlag,
  setUpdateTableFlag,
}) {
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const fetchPipelines = async () => {
    setLoading(true);
    try {
      const data = await getPipelines();
      setPipelines(data);
    } catch (error) {
      enqueueSnackbar("Error while fetching pipelines", { variant: "error" });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      fetchPipelines();
    }
  }, [updateTableFlag]);

  const handleDelete = async (id) => {
    try {
      await deletePipeline(id);
      enqueueSnackbar("Pipeline deleted successfully", { variant: "success" });
      fetchPipelines();
    } catch (error) {
      enqueueSnackbar("Failed to delete pipeline", { variant: "error" });
      console.error(error);
    }
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        minSize: 250,
      },
      {
        accessorKey: "created",
        header: "Created",
        minSize: 150,
        accessorFn: (row) => formatDate(row.created),
      },
      {
        accessorKey: "last_modified",
        header: "Edited",
        minSize: 150,
        accessorFn: (row) => formatDate(row.last_modified),
      },
      {
        id: "actions",
        header: "Actions",
        minSize: 160,
        Cell: ({ row }) => (
          <Grid container spacing={1} sx={{ py: 1 }}>
            <Grid>
              <Tooltip title="View">
                <IconButton
                  size="small"
                  onClick={() => navigate(`/app/pipelines/${row.original.id}`)}
                >
                  <ViewIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Grid>
            <Grid>
              <DeleteItemModal
                deleteFromTable={() => handleDelete(row.original.id)}
              />
            </Grid>
          </Grid>
        ),
      },
    ],
    [navigate],
  );

  const table = useMaterialReactTable({
    columns,
    data: pipelines,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: {
      density: "compact",
      sorting: [{ id: "last_modified", desc: true }],
      pagination: { pageSize: 5 },
    },
    enableGlobalFilter: true,
    state: { isLoading: loading },
    pageSizeOptions: [5, 10],
  });

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      <Grid
        container
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="h5">Current Pipelines</Typography>
        <Grid>
          <Grid container spacing={4}>
            <Grid>
              <Button
                variant="contained"
                onClick={() => navigate("/app/pipelines/new")}
                endIcon={<AddIcon />}
              >
                New Pipeline
              </Button>
            </Grid>
            <Grid>
              <Button
                variant="contained"
                onClick={fetchPipelines}
                endIcon={<UpdateIcon />}
              >
                Update
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {loading && <LinearProgress />}
      <MaterialReactTable table={table} />
    </Paper>
  );
}

PipelinesTable.propTypes = {
  handleOpenNewPipeline: PropTypes.func,
  updateTableFlag: PropTypes.bool.isRequired,
  setUpdateTableFlag: PropTypes.func.isRequired,
};

export default PipelinesTable;
