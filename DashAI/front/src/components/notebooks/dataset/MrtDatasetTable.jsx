import { useEffect, useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function MrtDatasetTable({
  fetchPage,
  initialPageSize = 5,
  deps = [],
  // Agregamos estos para no perder funcionalidad luego
  datasetPath,
  columnTypes = {},
}) {
  const { t } = useTranslation(["common"]);

  // Estados para la carga de datos
  const [data, setData] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Estados de la tabla (Paginación y Filtros)
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: initialPageSize,
  });
  const [columnFilters, setColumnFilters] = useState([]);

  // Efecto para cargar los datos (Server-side)
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // 1. Transformamos el Array de MRT al objeto que espera tu fetchPage
        // MRT: [{ id: 'name', value: 'John' }]
        // Tu API espera: { items: [{ field: 'name', value: 'John', operator: 'contains' }] }

        const muiFormattedFilters = {
          items: columnFilters.map((f) => ({
            field: f.id, // MRT usa 'id', tu API usa 'field'
            value: f.value,
            operator: "contains", // Valor por defecto para que tu backend no falle
          })),
        };

        // 2. Llamamos a fetchPage con el formato correcto
        const response = await fetchPage(
          pagination.pageIndex,
          pagination.pageSize,
          muiFormattedFilters, // <--- Ahora sí pasamos el objeto con .items
        );

        setData(response?.rows ?? []);
        setRowCount(response?.total ?? 0);
      } catch (error) {
        console.error("Error cargando datos:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [pagination.pageIndex, pagination.pageSize, columnFilters, ...deps]);

  // Definición de columnas dinámica basada en datos o columnTypes
  const columns = useMemo(() => {
    let columnKeys = [];

    // Opción 1: Si hay datos, usar las claves del primer registro
    if (data.length > 0) {
      columnKeys = Object.keys(data[0]).filter((key) => key !== "id");
    }
    // Opción 2: Si no hay datos, pero tenemos columnTypes, usar esas claves
    else if (Object.keys(columnTypes).length > 0) {
      columnKeys = Object.keys(columnTypes);
    }
    // Opción 3: Si no hay datos ni columnTypes, retornar vacío
    else {
      return [];
    }

    return columnKeys.map((key) => ({
      accessorKey: key,
      header: key,
      Header: () => (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
            {key}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {columnTypes[key]?.type || t("common:unknown")}
          </Typography>
        </Box>
      ),
    }));
  }, [data, columnTypes, t]);

  const table = useMaterialReactTable({
    columns,
    data,
    rowCount,
    enablePagination: true,
    manualPagination: true,
    manualFiltering: true,
    onPaginationChange: setPagination,
    onColumnFiltersChange: setColumnFilters,

    // --- AÑADE ESTO ---
    enableFilters: true,
    // Esta opción asegura que los filtros no se borren al esconder la barra
    maintainColumnFilters: true,

    state: {
      pagination,
      columnFilters,
      isLoading,
    },
    // ------------------

    muiCircularProgressProps: {
      color: "primary",
      thickness: 5,
      size: 45,
    },
  });

  return (
    <Box sx={{ width: "100%" }}>
      <MaterialReactTable table={table} />
    </Box>
  );
}
