import React, { useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  MRT_GlobalFilterTextField,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import {
  Box,
  IconButton,
  Tooltip,
} from "@mui/material";
import { Visibility, Delete } from "@mui/icons-material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../../utils";
import DocumentPreviewModal from "./DocumentPreviewModal";

export default function SimplifiedDocumentTable({
  documents,
  selectedIds,
  onToggle,
  onRemove,
  isLoading = false,
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [txtContent, setTxtContent] = useState("");
  
  const { i18n } = useTranslation(["common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const handleOpenPreview = async (doc) => {
    setPreviewDoc(doc);
    if (doc.file_type === "txt" && doc.preview) {
      try {
        const res = await fetch(doc.preview);
        const text = await res.text();
        setTxtContent(text);
      } catch (e) {
        setTxtContent("Error loading TXT file");
      }
    }
    setPreviewOpen(true);
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewDoc(null);
    setTxtContent("");
  };

  const selectedIdSet = useMemo(
    () => new Set(selectedIds.map((id) => String(id))),
    [selectedIds],
  );

  const columns = useMemo(
    () => [
      {
        accessorKey: "file_name",
        header: "Name",
        size: 250,
        Cell: ({ row }) => row.original.file_name,
      },
      {
        accessorKey: "file_type",
        header: "Type",
        size: 80,
        Cell: ({ row }) => row.original.file_type?.toUpperCase() || "-",
      },
      {
        accessorKey: "created",
        header: "Created",
        size: 150,
        Cell: ({ row }) => formatDate(row.original.created) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        size: 100,
        enableSorting: false,
        enableColumnFilter: false,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", gap: 1, justifyContent: "center" }}>
            <Tooltip title="Preview">
              <IconButton
                size="small"
                onClick={() => handleOpenPreview(row.original)}
              >
                <Visibility fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton
                size="small"
                onClick={() => onRemove(row.original.id)}
                color="error"
              >
                <Delete fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
    ],
    [onRemove],
  );

  const rowSelection = useMemo(
    () =>
      documents.reduce((acc, doc) => {
        acc[String(doc.id)] = selectedIdSet.has(String(doc.id));
        return acc;
      }, {}),
    [documents, selectedIdSet],
  );

  const table = useMaterialReactTable({
    columns,
    data: documents,
    enableSelectAll: true,
    enableRowSelection: true,
    selectAllMode: "all",
    enableColumnOrdering: false,
    enableColumnActions: false,
    enableColumnHiding: true,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enablePagination: true,
    enableBottomToolbar: true,
    enableTopToolbar: true,
    enableGlobalFilter: true,
    initialState: {
      columnVisibility: {
        file_type: false,
        created: false,
      },
      pagination: {
        pageIndex: 0,
        pageSize: 5,
      },
    },
    muiPaginationProps: {
      rowsPerPageOptions: [5, 10, 25, 50],
      showFirstButton: false,
      showLastButton: false,
    },
    muiTablePaperProps: {
      sx: {
        boxShadow: "none",
        borderRadius: 1,
        display: "flex",
        flexDirection: "column",
      },
    },
    muiTableContainerProps: {
      sx: {
        maxHeight: "none",
        flex: 1,
      },
    },
    muiTableHeadCellProps: {
      sx: {
        fontWeight: 600,
        backgroundColor: theme.palette.mode === "dark" 
          ? theme.palette.action.hover 
          : theme.palette.action.hover,
      },
    },
    muiTableBodyCellProps: {
      sx: {
        padding: "8px 16px",
      },
    },
    muiTableBodyRowProps: ({ row }) => ({
      sx: {
        backgroundColor: selectedIdSet.has(String(row.original.id))
          ? theme.palette.action.selected
          : "inherit",
        "&:hover": {
          backgroundColor: theme.palette.action.hover,
        },
      },
    }),
    rowNumberDisplayMode: "hidden",
    renderTopToolbarCustomActions: () => (
      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        <MRT_GlobalFilterTextField table={table} />
      </Box>
    ),
    state: {
      rowSelection,
      isLoading,
    },
    onRowSelectionChange: (updater) => {
      const nextRowSelection =
        typeof updater === "function" ? updater(rowSelection) : updater;

      const nextSelectedIdSet = new Set(
        Object.entries(nextRowSelection)
          .filter(([, isSelected]) => Boolean(isSelected))
          .map(([rowId]) => String(rowId)),
      );

      // Diff current vs next and toggle only what's changed
      documents.forEach((doc) => {
        const idKey = String(doc.id);
        const wasSelected = selectedIdSet.has(idKey);
        const isSelectedNow = nextSelectedIdSet.has(idKey);
        if (wasSelected !== isSelectedNow) {
          onToggle(doc.id);
        }
      });
    },
    getRowId: (row) => String(row.id),
    localization,
  });

  return (
    <>
      <Box sx={{ display: "flex", flexDirection: "column", width: "100%" }}>
        <MaterialReactTable table={table} />
      </Box>
      <DocumentPreviewModal
        open={previewOpen}
        onClose={handleClosePreview}
        document={previewDoc}
        txtContent={txtContent}
      />
    </>
  );
}

SimplifiedDocumentTable.propTypes = {
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      file_name: PropTypes.string.isRequired,
      created: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.instanceOf(Date),
      ]).isRequired,
      preview: PropTypes.string,
      file_type: PropTypes.string,
    }),
  ).isRequired,
  selectedIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  ).isRequired,
  onToggle: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
