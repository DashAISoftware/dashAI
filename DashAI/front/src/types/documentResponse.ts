export interface IDocumentResponse {
  id: number;
  file_name: string;
  created: Date;
  optional_metadata: Record<string, any> | null;
  file_url: string;
}