import React, { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";

import ContentHeader from "../mem-utils/ContentHeader";
import ActionButton from "../mem-utils/ActionButton";
import CreateProjectDialog from "../mem-utils/CreateProjectDialog";
import DataTable from "../mem-utils/DataTable";
import { useProjects } from "../mem-utils/ProjectContext";

export default function ProjectsContent({ selectedProject, onSelectProject }) {
  const theme = useTheme();
  const { projects, currentProject } = useProjects();
  const [creating, setCreating] = useState(false);

  const columns = [
    {
      key: "name",
      label: "Proyecto",
      width: "2fr",
      render: (project, selected) => (
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}
        >
          <Typography
            variant="body2"
            noWrap
            sx={{
              color: theme.palette.text.primary,
              fontWeight: selected ? 500 : 400,
            }}
          >
            {project.name}
          </Typography>
          {project.id === currentProject?.id && (
            <Chip label="Actual" size="small" variant="outlined" />
          )}
        </Box>
      ),
    },
    {
      key: "role",
      label: "Mi rol",
      render: (project) => project.my_role?.name ?? "Administrador",
    },
    {
      key: "member_count",
      label: "Integrantes",
      render: (project) => project.member_count,
    },
  ];

  const count = projects.length;

  return (
    <>
      <ContentHeader
        title="Proyectos"
        subtitle={
          count === 1
            ? "1 proyecto asociado a tu cuenta"
            : `${count} proyectos asociados a tu cuenta`
        }
        action={
          <ActionButton icon={AddIcon} onClick={() => setCreating(true)}>
            Nuevo proyecto
          </ActionButton>
        }
      />

      {count === 0 ? (
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.secondary, py: 4 }}
        >
          Aún no perteneces a ningún proyecto. Crea uno o pide a su dueño que te
          agregue con tu nickname.
        </Typography>
      ) : (
        <DataTable
          columns={columns}
          rows={projects}
          selectedId={selectedProject?.id}
          onRowClick={onSelectProject}
          actionLabel="Ver detalles"
        />
      )}

      <CreateProjectDialog open={creating} onClose={() => setCreating(false)} />
    </>
  );
}
