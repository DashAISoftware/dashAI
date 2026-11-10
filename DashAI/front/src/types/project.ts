import type { IRoleSummary } from "./auth";

export interface IProject {
  id: number;
  name: string;
  description: string | null;
  created: string;
  member_count: number;
  // Null for an administrator who is not a member
  my_role: IRoleSummary | null;
  my_permissions: string[];
}

export interface IProjectMember {
  user_id: number;
  username: string;
  social_name: string;
  role: IRoleSummary;
  joined: string;
}
