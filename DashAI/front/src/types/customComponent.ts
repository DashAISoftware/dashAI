export interface AbstractMethodInfo {
  name: string;
  signature: string;
  docstring: string;
}

export interface ClassAttributeInfo {
  name: string;
  type: string;
  default: unknown;
}

export interface BaseClassSummary {
  name: string;
  type: string;
  import_path: string;
  enabled: boolean;
}

export interface BaseClassInfo extends BaseClassSummary {
  docstring: string;
  abstract_methods: AbstractMethodInfo[];
  class_attributes: ClassAttributeInfo[];
  skeleton: string;
}

export interface ValidationRequest {
  source_code: string;
  class_name: string;
  base_class: string;
}

export interface ValidationResponse {
  ok: boolean;
  errors: string[];
  warnings: string[];
}

export interface CustomComponent {
  id: number;
  class_name: string;
  base_type: string;
  base_class: string;
  description: string | null;
  source_code: string;
  created: string;
  last_modified: string;
}

export interface CustomComponentCreate {
  class_name: string;
  base_class: string;
  source_code: string;
  description?: string | null;
}

export interface CustomComponentUpdate {
  class_name?: string;
  base_class?: string;
  source_code?: string;
  description?: string | null;
}
