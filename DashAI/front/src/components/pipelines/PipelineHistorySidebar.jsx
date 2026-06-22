import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Divider,
  IconButton,
  LinearProgress,
  Typography,
} from "@mui/material";
import {
  AddCircleOutline as AddIcon,
  MoreVert as MoreVertIcon,
  Update as UpdateIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";
import HistoryIcon from "@mui/icons-material/History";
import { useTheme } from "@mui/material/styles";
import { DataGrid, GridActionsCellItem, GridToolbar } from "@mui/x-data-grid";
import { Menu, MenuItem } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useSnackbar } from "notistack";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

import { deletePipeline, getPipelines } from "../../api/pipeline";
import { formatDate } from "../../utils";
import DeleteItemModal from "../custom/DeleteItemModal";

function PipelineHistorySidebar({ currentPipelineId }) {
  const theme = useTheme();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const [rowMenuAnchor, setRowMenuAnchor] = useState(null);
  const [rowMenuPipeline, setRowMenuPipeline] = useState(null);

  const fetchPipelines = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPipelines();
      setPipelines(data || []);
    } catch (error) {
      enqueueSnackbar("Error while fetching pipelines", { variant: "error" });
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  const handleDelete = async (id) => {
    try {
      await deletePipeline(id);
      enqueueSnackbar("Pipeline deleted successfully", { variant: "success" });
      if (String(currentPipelineId) === String(id)) {
        navigate("/app/pipelines");
      }
      fetchPipelines();
    } catch (error) {
      enqueueSnackbar("Failed to delete pipeline", { variant: "error" });
      console.error(error);
    }
  };

  const selectedPipeline = useMemo(() => {
    const parsedId = Number(currentPipelineId);
    return Number.isFinite(parsedId) ? [parsedId] : [];
  }, [currentPipelineId]);

  const handleOpenRowMenu = (event, pipeline) => {
    event.stopPropagation();
    setRowMenuAnchor(event.currentTarget);
    setRowMenuPipeline(pipeline);
  };

  const handleCloseRowMenu = () => {
    setRowMenuAnchor(null);
    setRowMenuPipeline(null);
  };

  const columns = useMemo(
    () => [
      {
        field: "name",
        headerName: "Name",
        minWidth: 150,
        flex: 1,
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 120,
        getActions: (params) => [
          <GridActionsCellItem
            key="view"
            icon={<ViewIcon />}
            label="View"
            onClick={() => navigate(`/app/pipelines/${params.id}`)}
          />,
          <GridActionsCellItem
            key="details"
            icon={<MoreVertIcon />}
            label="Details"
            onClick={(event) => handleOpenRowMenu(event, params.row)}
          />,
          <DeleteItemModal
            key="delete"
            deleteFromTable={() => handleDelete(params.id)}
          />,
        ],
      },
    ],
    [navigate, handleDelete],
  );

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          minHeight: 64,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <HistoryIcon fontSize="small" sx={{ color: theme.palette.text.primary }} />
          <Typography variant="subtitle1">Pipelines History</Typography>
        </Box>
      </Box>
      <Divider sx={{ width: "100%", bgcolor: theme.palette.ui.borderDark }} />

      <Box sx={{ px: 2, py: 1.5, display: "flex", gap: 0.75, minHeight: 64 }}>
        <Button
          variant="contained"
          onClick={() => navigate("/app/pipelines/new")}
          startIcon={<AddIcon />}
          sx={{ flex: 1.5, minWidth: 0 }}
        >
          New Pipeline
        </Button>
        <Button
          variant="outlined"
          onClick={fetchPipelines}
          startIcon={<UpdateIcon />}
          sx={{ flex: 1, minWidth: 0 }}
        >
          Update
        </Button>
      </Box>

      <Divider sx={{ width: "90%", bgcolor: theme.palette.ui.borderDark, mx: "auto" }} />

      <Box sx={{ flex: 1, minHeight: 0, p: 1.5 }}>
        <DataGrid
          rows={pipelines}
          columns={columns}
          sortModel={[{ field: "last_modified", sort: "desc" }]}
          loading={loading}
          disableRowSelectionOnClick
          rowSelectionModel={selectedPipeline}
          pageSizeOptions={[5, 10]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 5 },
            },
          }}
          slots={{
            toolbar: GridToolbar,
            loadingOverlay: LinearProgress,
          }}
          sx={{
            height: "100%",
            borderColor: theme.palette.ui.borderLight,
            "& .MuiDataGrid-columnHeaders": {
              borderBottomColor: theme.palette.ui.borderLight,
            },
            "& .MuiDataGrid-cell": {
              borderBottomColor: theme.palette.ui.borderLight,
            },
          }}
        />

        <Menu
          anchorEl={rowMenuAnchor}
          open={Boolean(rowMenuAnchor)}
          onClose={handleCloseRowMenu}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <MenuItem disabled>
            Created: {rowMenuPipeline ? formatDate(rowMenuPipeline.created) : "-"}
          </MenuItem>
          <MenuItem disabled>
            Edited: {rowMenuPipeline ? formatDate(rowMenuPipeline.last_modified) : "-"}
          </MenuItem>
        </Menu>
      </Box>
    </SideBar>
  );
}

export default PipelineHistorySidebar;
