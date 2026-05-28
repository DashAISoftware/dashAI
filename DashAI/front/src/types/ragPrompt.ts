export interface IRAGPrompt {
  id: number;
  class_name: string;
  name: string;
  created?: string;
  last_modified?: string;
  parameters: {
    template: string;
    language?: string;
  };
}
