import api from "./api";
import type { IProject, IProjectMember } from "../types/project";

const projectEndpoint = "/v1/project";

// The project the user is working in. Set by the ProjectProvider and read by
// the calls of project-scoped resources (datasets for now), so the views that
// make those calls do not need to pass it around
let currentProjectId: number | null = null;

export const setCurrentProjectId = (projectId: number | null): void => {
  currentProjectId = projectId;
};

export const getCurrentProjectId = (): number | null => currentProjectId;

export const getMyProjects = async (): Promise<IProject[]> => {
  const response = await api.get<IProject[]>(`${projectEndpoint}/`);
  return response.data;
};

export const createProject = async (
  name: string,
  description?: string,
): Promise<IProject> => {
  const response = await api.post<IProject>(`${projectEndpoint}/`, {
    name,
    description,
  });
  return response.data;
};

export const getProject = async (projectId: number): Promise<IProject> => {
  const response = await api.get<IProject>(`${projectEndpoint}/${projectId}`);
  return response.data;
};

export const getMembers = async (
  projectId: number,
): Promise<IProjectMember[]> => {
  const response = await api.get<IProjectMember[]>(
    `${projectEndpoint}/${projectId}/members`,
  );
  return response.data;
};

export const addMember = async (
  projectId: number,
  username: string,
  roleUid: string,
): Promise<IProjectMember> => {
  const response = await api.post<IProjectMember>(
    `${projectEndpoint}/${projectId}/members`,
    { username, role_uid: roleUid },
  );
  return response.data;
};

export const changeMemberRole = async (
  projectId: number,
  userId: number,
  roleUid: string,
): Promise<IProjectMember> => {
  const response = await api.patch<IProjectMember>(
    `${projectEndpoint}/${projectId}/members/${userId}`,
    { role_uid: roleUid },
  );
  return response.data;
};

export const removeMember = async (
  projectId: number,
  userId: number,
): Promise<void> => {
  await api.delete(`${projectEndpoint}/${projectId}/members/${userId}`);
};
