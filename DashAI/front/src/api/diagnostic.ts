import api from "./api";

export interface IDiagnostic {
  id: number;
  run_id: number;
  diagnostic_name: string;
  split: string;
  parameters: object;
  artifacts_path: string | null;
  status: number;
  created: string;
}

export const getDiagnostics = async (runId: number): Promise<IDiagnostic[]> => {
  const response = await api.get<IDiagnostic[]>("/v1/diagnostic/", {
    params: { run_id: runId },
  });
  return response.data;
};

export const getDiagnosticArtifacts = async (
  diagnosticId: number,
): Promise<any[]> => {
  const response = await api.get<any[]>(
    `/v1/diagnostic/${diagnosticId}/artifacts`,
  );
  return response.data;
};

export const createDiagnostic = async (
  runId: number,
  diagnosticName: string,
  split: string,
  parameters: object = {},
): Promise<IDiagnostic> => {
  const response = await api.post<IDiagnostic>("/v1/diagnostic/", {
    run_id: runId,
    diagnostic_name: diagnosticName,
    split,
    parameters,
  });
  return response.data;
};

export const deleteDiagnostic = async (diagnosticId: number): Promise<void> => {
  await api.delete(`/v1/diagnostic/${diagnosticId}`);
};
