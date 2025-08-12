import { useEffect, useMemo, useState } from "react";
import { DataGrid, GridToolbar, GridColDef } from "@mui/x-data-grid";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import { getDatasetFile } from "../../api/datasets";

export default function DatasetView({ dataset }) {
  const [rows, setRows] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [loading, setLoading] = useState(false);

  // paginación controlada (server-side)
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 5,
  });

  // Carga de datos cuando cambian page/pageSize o el dataset.path
  useEffect(() => {
    let alive = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        const { page, pageSize } = paginationModel;
        const data = await getDatasetFile(dataset.file_path, page, pageSize);
        if (!alive) return;

        // DataGrid requiere un id. Creamos uno estable dentro de la página actual.
        const withIds = (data.rows ?? []).map((r, i) => ({
          id: page * pageSize + i, // si tu backend tiene un id real, usa ese en su lugar
          ...r,
        }));

        setRows(withIds);
        setRowCount(data.total ?? withIds.length);
      } catch (e) {
        console.error(e);
        setRows([]);
        setRowCount(0);
      } finally {
        if (alive) setLoading(false);
      }
    };
    fetchData();
    return () => {
      alive = false;
    };
  }, [dataset.file_path, paginationModel]);

  // Columns dinámicas a partir de las keys del primer row
  const columns = useMemo(() => {
    const first = rows[0];
    if (!first) return [];
    return Object.keys(first)
      .filter((k) => k !== "id") // ya añadimos id en rows
      .map((field) => ({
        field, // admite espacios
        headerName: field,
        flex: 1,
        minWidth: 120,
      }));
  }, [rows]);

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      {/* Título y botón */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="h5" component="h2">
          {dataset.name}
        </Typography>
        <Grid item>
          <Grid container spacing={2}>
            <Grid item>
              <Button
                variant="contained"
                // onClick={handleNewDataset}
                endIcon={<AddIcon />}
              >
                New Dataset
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* Tabla con paginación server-side */}
      <DataGrid
        rows={rows}
        columns={columns}
        rowCount={rowCount}
        loading={loading}
        autoHeight
        disableRowSelectionOnClick
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        pageSizeOptions={[5, 10, 25]}
        slots={{
          toolbar: GridToolbar,
          loadingOverlay: LinearProgress,
        }}
      />
    </Paper>
  );
}
