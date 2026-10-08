import React, { useState } from "react";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import ProfileLayout from "../mem-utils/ProfileLayout";
import DetailPanel, {
  DetailField,
  DetailSection,
} from "../mem-utils/DetailPanel";
import ActionButton from "../mem-utils/ActionButton";
import ProjectsContent from "../utils/ProjectsContent";

function ProjectDetails({ project, onClose }) {
  const theme = useTheme();

  return (
    <DetailPanel
      title={project?.name}
      subtitle={project?.id}
      onClose={onClose}
      emptyMessage="Selecciona un proyecto para visualizar información adicional."
    >
      {project && (
        <>
          <DetailSection label="Información">
            <DetailField label="Creador">{project.owner}</DetailField>
            <DetailField label="Integrantes">
              {project.members} miembros
            </DetailField>
          </DetailSection>

          <DetailSection label="Equipo">
            <Typography
              variant="body2"
              sx={{ color: theme.palette.text.secondary, lineHeight: 1.6 }}
            >
              {project.teamSummary}
            </Typography>
            <ActionButton sx={{ mt: 2 }}>Ver integrantes</ActionButton>
          </DetailSection>

          <DetailSection label="Mi acceso">
            <DetailField label="Rol">{project.role}</DetailField>
            <DetailField label="Permisos">
              {project.permissions} permisos asignados
            </DetailField>
            <ActionButton sx={{ mt: 2 }}>Ver permisos</ActionButton>
          </DetailSection>
        </>
      )}
    </DetailPanel>
  );
}

export default function Projects() {
  const [selectedProject, setSelectedProject] = useState(null);

  return (
    <ProfileLayout
      title="Mis proyectos"
      subtitle="Visualiza los proyectos a los que perteneces y tu nivel de acceso."
      rightPanel={
        <ProjectDetails
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
        />
      }
    >
      <ProjectsContent
        selectedProject={selectedProject}
        onSelectProject={setSelectedProject}
      />
    </ProfileLayout>
  );
}
