import React, { useState } from "react";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import ProfileLayout from "../mem-utils/ProfileLayout";
import DetailPanel, {
  DetailField,
  DetailSection,
} from "../mem-utils/DetailPanel";
import ActionButton from "../mem-utils/ActionButton";
import ProjectMembers from "../mem-utils/ProjectMembers";
import { useProjects } from "../mem-utils/ProjectContext";
import ProjectsContent from "../utils/ProjectsContent";

function ProjectDetails({ project, onClose }) {
  const theme = useTheme();
  const { currentProject, selectProject } = useProjects();

  return (
    <DetailPanel
      title={project?.name}
      subtitle={project?.description}
      onClose={onClose}
      emptyMessage="Selecciona un proyecto para visualizar información adicional."
    >
      {project && (
        <>
          <DetailSection label="Información">
            <DetailField label="Creado">
              {new Date(project.created).toLocaleDateString("es-CL")}
            </DetailField>
            <DetailField label="Integrantes">
              {project.member_count}
            </DetailField>
            {project.id === currentProject?.id ? (
              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  mt: 2,
                  color: theme.palette.text.disabled,
                }}
              >
                Es el proyecto en el que estás trabajando.
              </Typography>
            ) : (
              <ActionButton
                sx={{ mt: 2 }}
                onClick={() => selectProject(project.id)}
              >
                Trabajar en este proyecto
              </ActionButton>
            )}
          </DetailSection>

          <DetailSection label="Mi acceso">
            <DetailField label="Rol">
              {project.my_role?.name ?? "Administrador"}
            </DetailField>
            <DetailField label="Permisos">
              {project.my_permissions.length} permisos en este proyecto
            </DetailField>
          </DetailSection>

          <DetailSection label="Integrantes">
            <ProjectMembers project={project} />
          </DetailSection>
        </>
      )}
    </DetailPanel>
  );
}

export default function Projects() {
  const { projects } = useProjects();
  const [selectedId, setSelectedId] = useState(null);

  // Read from the list, so the panel follows refreshes (a new member count)
  // and closes if the user leaves the project
  const selectedProject = projects.find((p) => p.id === selectedId) ?? null;

  return (
    <ProfileLayout
      title="Mis proyectos"
      subtitle="Visualiza los proyectos a los que perteneces, tu nivel de acceso y sus integrantes."
      rightPanel={
        <ProjectDetails
          project={selectedProject}
          onClose={() => setSelectedId(null)}
        />
      }
    >
      <ProjectsContent
        selectedProject={selectedProject}
        onSelectProject={(project) => setSelectedId(project.id)}
      />
    </ProfileLayout>
  );
}
