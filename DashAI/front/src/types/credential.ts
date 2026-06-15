export interface ICredential {
  name: string;
  display_name: string;
  is_authenticated: boolean;
  key: string | null;
}
