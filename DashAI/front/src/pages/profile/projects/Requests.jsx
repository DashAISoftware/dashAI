import React, { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import ProfileLayout from "../mem-utils/ProfileLayout";
import DetailPanel, {
  DetailField,
  DetailSection,
} from "../mem-utils/DetailPanel";
import RequestsContent from "../utils/RequestsContent";

function RequestDetails({ request, onClose }) {
  const theme = useTheme();

  return (
    <DetailPanel
      title={request?.subject}
      subtitle={request?.id}
      onClose={onClose}
      emptyMessage="Selecciona una solicitud para visualizar información adicional."
    >
      {request && (
        <>
          <DetailSection label="Información">
            <DetailField label="Proyecto">{request.project}</DetailField>
            <DetailField label="Solicitante">{request.requester}</DetailField>
            <DetailField label="Estado">{request.status}</DetailField>
          </DetailSection>

          <DetailSection label="Permisos solicitados">
            {request.permissions.map((permission) => (
              <Box key={permission} sx={{ py: 1 }}>
                <Typography
                  variant="body2"
                  sx={{
                    color: theme.palette.text.secondary,
                    fontFamily: '"Geist Mono", monospace',
                    fontSize: "0.8rem",
                  }}
                >
                  {permission}
                </Typography>
              </Box>
            ))}
          </DetailSection>

          <DetailSection label="Motivo">
            <Typography
              variant="body2"
              sx={{ color: theme.palette.text.secondary, lineHeight: 1.6 }}
            >
              {request.reason}
            </Typography>
          </DetailSection>
        </>
      )}
    </DetailPanel>
  );
}

export default function Requests() {
  const [selectedRequest, setSelectedRequest] = useState(null);

  return (
    <ProfileLayout
      title="Mis solicitudes"
      subtitle="Consulta las solicitudes de acceso y permisos asociadas a tu cuenta."
      rightPanel={
        <RequestDetails
          request={selectedRequest}
          onClose={() => setSelectedRequest(null)}
        />
      }
    >
      <RequestsContent
        selectedRequest={selectedRequest}
        onSelectRequest={setSelectedRequest}
      />
    </ProfileLayout>
  );
}
