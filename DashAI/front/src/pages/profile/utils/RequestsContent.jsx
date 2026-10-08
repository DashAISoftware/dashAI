import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";

import ContentHeader from "../mem-utils/ContentHeader";
import ActionButton from "../mem-utils/ActionButton";
import DataTable from "../mem-utils/DataTable";
import { MOCK_USER } from "../mem-utils/mockUser";

const REQUESTS = [
  {
    id: "REQ-001",
    subject: "Acceso de edición al proyecto",
    project: "PRJ-001",
    status: "Pendiente",
    requester: MOCK_USER.socialName,
    permissions: ["datasets.write", "models.execute", "workflows.write"],
    reason:
      "Necesito modificar los datasets utilizados por el workflow de entrenamiento.",
  },
  {
    id: "REQ-002",
    subject: "Acceso a modelos generativos",
    project: "PRJ-003",
    status: "Aprobada",
    requester: MOCK_USER.socialName,
    permissions: ["generative.read", "generative.execute"],
    reason:
      "Necesito utilizar las herramientas generativas disponibles en el proyecto.",
  },
  {
    id: "REQ-003",
    subject: "Permiso para modificar datasets",
    project: "PRJ-002",
    status: "Rechazada",
    requester: MOCK_USER.socialName,
    permissions: ["datasets.write"],
    reason:
      "Se requiere acceso de edición para preparar los datos del proyecto.",
  },
];

export default function RequestsContent({ selectedRequest, onSelectRequest }) {
  const theme = useTheme();

  const columns = [
    {
      key: "subject",
      label: "Solicitud",
      width: "2fr",
      render: (request, selected) => (
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.primary,
              fontWeight: selected ? 500 : 400,
            }}
          >
            {request.subject}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: theme.palette.text.disabled,
              fontFamily: '"Geist Mono", monospace',
            }}
          >
            {request.id}
          </Typography>
        </Box>
      ),
    },
    {
      key: "project",
      label: "Proyecto",
      render: (request) => (
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.secondary,
            fontFamily: '"Geist Mono", monospace',
            fontSize: "0.8rem",
          }}
        >
          {request.project}
        </Typography>
      ),
    },
    { key: "status", label: "Estado" },
  ];

  return (
    <>
      <ContentHeader
        title="Solicitudes"
        subtitle={`${REQUESTS.length} solicitudes asociadas a tu cuenta`}
        action={<ActionButton icon={AddIcon}>Solicitar acceso</ActionButton>}
      />

      <DataTable
        columns={columns}
        rows={REQUESTS}
        selectedId={selectedRequest?.id}
        onRowClick={onSelectRequest}
        actionLabel="Ver detalles"
      />
    </>
  );
}
