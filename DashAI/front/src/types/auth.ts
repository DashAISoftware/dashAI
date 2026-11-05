export interface IRoleSummary {
  uid: string;
  name: string;
}

export interface IUser {
  id: number;
  username: string;
  email: string;
  social_name: string;
  bio: string | null;
  phone: string | null;
  github: string | null;
  linkedin: string | null;
  legal_name: string | null;
  organization: string | null;
  position: string | null;
  global_role: IRoleSummary;
  permissions: string[];
  last_login: string | null;
  created: string;
}

export interface IRegisterParams {
  username: string;
  email: string;
  password: string;
  social_name: string;
}

export interface IProfileUpdate {
  social_name?: string;
  bio?: string | null;
  phone?: string | null;
  github?: string | null;
  linkedin?: string | null;
}
