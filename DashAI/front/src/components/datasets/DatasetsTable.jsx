import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
  Image as ImageIcon,
} from "@mui/icons-material";
import {
  Button,
  Grid,
  Paper,
  Typography,
  LinearProgress,
  IconButton,
} from "@mui/material";
import DeleteItemModal from "../custom/DeleteItemModal";
import EditDatasetModal from "./EditDatasetModal";
import DatasetSummaryModal from "./DatasetSummaryModal";
import ImageColumnsInfoModal from "./ImageColumnsInfoModal";
import {
  getDatasets as getDatasetsRequest,
  deleteDataset as deleteDatasetRequest,
  getImageColumnsInfo,
} from "../../api/datasets";
import { useSnackbar } from "notistack";
import { formatDate } from "../../utils/index";

function DatasetsTable({
  handleNewDataset,
  updateTableFlag,
  setUpdateTableFlag,
}) {
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState([]);
  const [showImageInfo, setShowImageInfo] = useState(false);
  const [imageColumnsInfo, setImageColumnsInfo] = useState({});
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const { enqueueSnackbar } = useSnackbar();

  // Usar un ref para almacenar el último ID de dataset conocido
  const lastKnownMaxIdRef = useRef(0);

  // Función para verificar imágenes en un dataset
  const checkImagesForDataset = async (datasetId) => {
    try {
      setLoading(true);
      const info = await getImageColumnsInfo(datasetId);

      if (info && Object.keys(info).length > 0) {
        setImageColumnsInfo(info);
        setSelectedDatasetId(datasetId);
        setShowImageInfo(true);
      } else {
        enqueueSnackbar("No image columns found in this dataset", {
          variant: "info",
        });
      }
    } catch (error) {
      console.error(
        `Error fetching image columns info for dataset ${datasetId}:`,
        error,
      );
      enqueueSnackbar("Error checking image columns", { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Función para verificar si hay un nuevo dataset y mostrar su información de imágenes
  const checkForNewDataset = (datasets) => {
    if (!datasets || datasets.length === 0) return;

    // Encontrar el ID máximo actual
    const currentMaxId = Math.max(...datasets.map((d) => d.id));

    // Si hay un nuevo dataset (ID mayor que el último conocido)
    if (currentMaxId > lastKnownMaxIdRef.current) {
      // Actualizar el último ID conocido
      lastKnownMaxIdRef.current = currentMaxId;

      // Verificar imágenes para el nuevo dataset
      checkImagesForDataset(currentMaxId);
    }
  };

  const getDatasets = async () => {
    setLoading(true);
    try {
      const fetchedDatasets = await getDatasetsRequest();
      setDatasets(fetchedDatasets);

      // Si se está actualizando la tabla (posiblemente después de crear un dataset)
      if (updateTableFlag) {
        checkForNewDataset(fetchedDatasets);
      }
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset table.");
      console.error("Error fetching datasets:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteDataset = async (id) => {
    try {
      await deleteDatasetRequest(id);
      enqueueSnackbar("Dataset successfully deleted.", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Error when trying to delete the dataset");
      console.error("Error deleting dataset:", error);
    }
  };

  const createDeleteHandler = React.useCallback(
    (id) => () => {
      deleteDataset(id);
      setUpdateTableFlag(true);
    },
    [],
  );

  const handleCloseImageInfo = () => {
    setShowImageInfo(false);
  };

  // Inicializar el último ID conocido al montar el componente
  useEffect(() => {
    const initializeLastKnownId = async () => {
      try {
        const initialDatasets = await getDatasetsRequest();
        if (initialDatasets && initialDatasets.length > 0) {
          lastKnownMaxIdRef.current = Math.max(
            ...initialDatasets.map((d) => d.id),
          );
        }
        setDatasets(initialDatasets);
      } catch (error) {
        console.error("Error initializing datasets:", error);
      } finally {
        setLoading(false);
      }
    };

    initializeLastKnownId();
  }, []);

  // Actualizar cuando cambia updateTableFlag
  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      getDatasets();
    }
  }, [updateTableFlag]);

  const columns = React.useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 50,
        editable: false,
      },
      {
        field: "name",
        headerName: "Name",
        minWidth: 250,
        editable: false,
      },
      {
        field: "created",
        headerName: "Created",
        minWidth: 140,
        editable: false,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "last_modified",
        headerName: "Edited",
        type: Date,
        minWidth: 140,
        editable: false,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 180,
        getActions: (params) => [
          <EditDatasetModal
            key="edit-component"
            name={params.row.name}
            datasetId={params.id}
            updateDatasets={() => setUpdateTableFlag(true)}
          />,
          <DeleteItemModal
            key="delete-component"
            deleteFromTable={createDeleteHandler(params.id)}
          />,
          <DatasetSummaryModal
            key="dataset-summary-component"
            datasetId={params.id}
          />,
        ],
      },
    ],
    [createDeleteHandler],
  );

  return (
    <React.Fragment>
      <Paper sx={{ py: 4, px: 6 }}>
        <Grid
          container
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="h5" component="h2">
            Current datasets
          </Typography>
          <Grid item>
            <Grid container spacing={2}>
              <Grid item>
                <Button
                  variant="contained"
                  onClick={handleNewDataset}
                  endIcon={<AddIcon />}
                >
                  New Dataset
                </Button>
              </Grid>
              <Grid item>
                <Button
                  variant="contained"
                  onClick={() => setUpdateTableFlag(true)}
                  endIcon={<UpdateIcon />}
                >
                  Update
                </Button>
              </Grid>
            </Grid>
          </Grid>
        </Grid>

        <DataGrid
          rows={datasets}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
          }}
          sortModel={[{ field: "id", sort: "desc" }]}
          pageSize={5}
          pageSizeOptions={[5, 10]}
          disableRowSelectionOnClick
          autoHeight
          loading={loading}
          slots={{
            toolbar: GridToolbar,
            loadingOverlay: LinearProgress,
          }}
        />
      </Paper>

      {/* Modal para mostrar información de columnas de imágenes */}
      <ImageColumnsInfoModal
        open={showImageInfo}
        onClose={handleCloseImageInfo}
        imageColumnsInfo={imageColumnsInfo}
        datasetId={selectedDatasetId}
        updateDatasets={() => setUpdateTableFlag(true)}
      />
    </React.Fragment>
  );
}

DatasetsTable.propTypes = {
  handleNewDataset: PropTypes.func.isRequired,
  updateTableFlag: PropTypes.bool.isRequired,
  setUpdateTableFlag: PropTypes.func.isRequired,
};

export default DatasetsTable;
