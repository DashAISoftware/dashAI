import React, { useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import ProfileLayout from "../mem-utils/ProfileLayout";
import DetailPanel, {
  DetailField,
  DetailSection,
} from "../mem-utils/DetailPanel";
import { MOCK_ROLES, PERMISSIONS } from "../mem-utils/mockInstance";
import ManageRolesContent from "../utils/ManageRolesContent";

// Instance permissions only make sense in a global role
function permissionsFor(role) {
  return role.scope === "Global"
    ? PERMISSIONS
    : PERMISSIONS.filter((permission) => !permission.instance);
}

function RoleDetails({ role, onTogglePermission, onClose }) {
  const theme = useTheme();
  const available = role ? permissionsFor(role) : [];
  const categories = [
    ...new Set(available.map((permission) => permission.category)),
  ];

  return (
    <DetailPanel
      title={role?.name}
      subtitle={role && `Alcance: ${role.scope}`}
      onClose={onClose}
      emptyMessage="Selecciona un rol para ver y ajustar sus permisos."
    >
      {role && (
        <>
          <DetailSection label="Información">
            <DetailField label="Descripción">{role.description}</DetailField>
            <DetailField label="Permisos asignados">
              {role.permissions.length} de {available.length}
            </DetailField>
            {role.system && (
              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  mt: 2,
                  color: theme.palette.text.disabled,
                }}
              >
                Rol fijo: sus permisos se calculan automáticamente y no se
                pueden modificar.
              </Typography>
            )}
          </DetailSection>

          {categories.map((category) => (
            <DetailSection key={category} label={category}>
              {available
                .filter((permission) => permission.category === category)
                .map((permission) => (
                  <FormControlLabel
                    key={permission.uid}
                    disabled={role.system}
                    control={
                      <Checkbox
                        size="small"
                        checked={role.permissions.includes(permission.uid)}
                        onChange={() => onTogglePermission(permission.uid)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">
                          {permission.description}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            color: theme.palette.text.disabled,
                            fontFamily: '"Geist Mono", monospace',
                          }}
                        >
                          {permission.uid}
                        </Typography>
                      </Box>
                    }
                    sx={{ display: "flex", alignItems: "flex-start", mb: 1 }}
                  />
                ))}
            </DetailSection>
          ))}
        </>
      )}
    </DetailPanel>
  );
}

export default function ManageRoles() {
  const [roles, setRoles] = useState(MOCK_ROLES);
  const [selectedId, setSelectedId] = useState(null);

  const selectedRole = roles.find((role) => role.id === selectedId) ?? null;

  const togglePermission = (uid) =>
    setRoles((previous) =>
      previous.map((role) => {
        if (role.id !== selectedId) return role;
        const permissions = role.permissions.includes(uid)
          ? role.permissions.filter((permission) => permission !== uid)
          : [...role.permissions, uid];
        return { ...role, permissions };
      }),
    );

  return (
    <ProfileLayout
      title="Roles y permisos"
      subtitle="Define qué puede hacer cada rol dentro de la instancia y de los proyectos."
      rightPanel={
        <RoleDetails
          role={selectedRole}
          onTogglePermission={togglePermission}
          onClose={() => setSelectedId(null)}
        />
      }
    >
      <ManageRolesContent
        roles={roles}
        selectedRoleId={selectedId}
        onSelectRole={setSelectedId}
      />
    </ProfileLayout>
  );
}
