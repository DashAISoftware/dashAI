import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import PropTypes from "prop-types";

import * as projectsApi from "../../../api/projects";
import { useSession } from "./SessionContext";

const ProjectContext = createContext(null);

const storageKey = (userId) => `dashai.currentProject.${userId}`;

// Browser storage can be unavailable (private windows, blocked site data);
// losing the remembered project is harmless
function readStoredProject(userId) {
  try {
    const value = window.localStorage.getItem(storageKey(userId));
    return value === null ? null : Number(value);
  } catch {
    return null;
  }
}

function storeProject(userId, projectId) {
  try {
    window.localStorage.setItem(storageKey(userId), String(projectId));
  } catch {
    // Ignored, see readStoredProject
  }
}

/**
 * Keeps the projects of the logged-in user and the one they are working in.
 *
 * The current project is remembered per user in the browser. If it is no
 * longer in the list (the user left or was removed), the first project is
 * used instead.
 */
export function ProjectProvider({ children }) {
  const { user, loading: sessionLoading } = useSession();
  const [projects, setProjects] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  // User whose projects are loaded; undefined before the first load
  const [loadedFor, setLoadedFor] = useState(undefined);

  const userId = user?.id ?? null;
  // Derived instead of stored, so it is already true in the very render in
  // which the user changes
  const loading = sessionLoading || loadedFor !== userId;

  const refresh = useCallback(async () => {
    if (userId === null) {
      setProjects([]);
      setCurrentId(null);
      return [];
    }
    const mine = await projectsApi.getMyProjects();
    setProjects(mine);
    setCurrentId((previous) => {
      const wanted = previous ?? readStoredProject(userId);
      return mine.some((p) => p.id === wanted) ? wanted : mine[0]?.id ?? null;
    });
    return mine;
  }, [userId]);

  useEffect(() => {
    if (sessionLoading) return;
    setCurrentId(null);
    refresh()
      .catch(() => setProjects([]))
      .finally(() => setLoadedFor(userId));
  }, [sessionLoading, refresh, userId]);

  const selectProject = useCallback(
    (projectId) => {
      setCurrentId(projectId);
      if (userId !== null) storeProject(userId, projectId);
    },
    [userId],
  );

  const createProject = useCallback(
    async (name, description) => {
      const project = await projectsApi.createProject(name, description);
      await refresh();
      selectProject(project.id);
      return project;
    },
    [refresh, selectProject],
  );

  const currentProject = projects.find((p) => p.id === currentId) ?? null;

  // Set while rendering, not in an effect: the children's effects run before
  // this component's, and their first requests must already carry the project
  projectsApi.setCurrentProjectId(currentProject?.id ?? null);

  // Permissions inside the current project, as computed by the backend
  const canInProject = useCallback(
    (permission) =>
      Boolean(currentProject) &&
      currentProject.my_permissions.includes(permission),
    [currentProject],
  );

  const value = useMemo(
    () => ({
      projects,
      currentProject,
      loading,
      selectProject,
      createProject,
      refresh,
      canInProject,
    }),
    [
      projects,
      currentProject,
      loading,
      selectProject,
      createProject,
      refresh,
      canInProject,
    ],
  );

  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
}

ProjectProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useProjects() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProjects must be used within a ProjectProvider");
  }
  return context;
}

/**
 * Remounts its children when the user or the current project changes, so
 * every view and data provider below loads its data again for the new
 * project instead of showing the previous one.
 */
export function ProjectScope({ children }) {
  const { user } = useSession();
  const { currentProject, loading } = useProjects();

  // Waiting avoids a first load without the project followed by a second one
  if (user && loading) return null;

  const key = `${user?.id ?? "anonymous"}:${currentProject?.id ?? "none"}`;
  return <React.Fragment key={key}>{children}</React.Fragment>;
}

ProjectScope.propTypes = {
  children: PropTypes.node.isRequired,
};
