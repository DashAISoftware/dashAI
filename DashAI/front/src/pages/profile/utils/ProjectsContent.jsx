import React from "react";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";

import ContentHeader from "../mem-utils/ContentHeader";
import ActionButton from "../mem-utils/ActionButton";
import DataTable from "../mem-utils/DataTable";
import { MOCK_USER } from "../mem-utils/mockUser";

const USER_FIRST_NAME = MOCK_USER.socialName.split(" ")[0];

const PROJECTS = [
  {
    id: "PRJ-001",
    name: "Proyecto de Machine Learning",
    role: "Editor",
    owner: MOCK_USER.socialName,
    members: 6,
    permissions: 7,
    teamSummary: `${USER_FIRST_NAME}, Ana, Pedro y 3 integrantes más.`,
  },
  {
    id: "PRJ-002",
    name: "Análisis de datasets",
    role: "Viewer",
    owner: "Ana Pérez",
    members: 4,
    permissions: 3,
    teamSummary: `Ana, ${USER_FIRST_NAME}, Pedro y un integrante más.`,
  },
  {
    id: "PRJ-003",
    name: "Modelos generativos",
    role: "Owner",
    owner: MOCK_USER.socialName,
    members: 3,
    permissions: 10,
    teamSummary: `${USER_FIRST_NAME}, Diego y Catalina.`,
  },
];

export default function ProjectsContent({ selectedProject, onSelectProject }) {
  const theme = useTheme();

  const columns = [
    {
      key: "name",
      label: "Proyecto",
      width: "2fr",
      render: (project, selected) => (
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.primary,
            fontWeight: selected ? 500 : 400,
          }}
        >
          {project.name}
        </Typography>
      ),
    },
    {
      key: "id",
      label: "ID",
      render: (project) => (
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.disabled,
            fontFamily: '"Geist Mono", monospace',
            fontSize: "0.8rem",
          }}
        >
          {project.id}
        </Typography>
      ),
    },
    { key: "role", label: "Rol" },
  ];

  return (
    <>
      <ContentHeader
        title="Proyectos"
        subtitle={`${PROJECTS.length} proyectos asociados a tu cuenta`}
        action={<ActionButton icon={AddIcon}>Nuevo proyecto</ActionButton>}
      />

      <DataTable
        columns={columns}
        rows={PROJECTS}
        selectedId={selectedProject?.id}
        onRowClick={onSelectProject}
        actionLabel="Ver detalles"
      />
    </>
  );
}
