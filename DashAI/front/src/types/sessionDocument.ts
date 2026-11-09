export interface ISessionDocument {
  id: number;
  name: string;
  file_name: string;
  file_type: string;
  status: number;
  total_pages: number | null;
  content_counts: Record<string, number> | null;
  created: string;
  folder_id: number | null;
  folder_name: string | null;
}
