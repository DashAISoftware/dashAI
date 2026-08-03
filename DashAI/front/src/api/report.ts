import api from "./api";

export interface IReport {
  id: number;
  run_id: number;
  report_name: string;
  split: string;
  parameters: object;
  artifacts_path: string | null;
  status: number;
  created: string;
}

export const getReports = async (runId: number): Promise<IReport[]> => {
  const response = await api.get<IReport[]>("/v1/report/", {
    params: { run_id: runId },
  });
  return response.data;
};

export const getReportArtifacts = async (reportId: number): Promise<any[]> => {
  const response = await api.get<any[]>(`/v1/report/${reportId}/artifacts`);
  return response.data;
};

export const createReport = async (
  runId: number,
  reportName: string,
  split: string,
  parameters: object = {},
): Promise<IReport> => {
  const response = await api.post<IReport>("/v1/report/", {
    run_id: runId,
    report_name: reportName,
    split,
    parameters,
  });
  return response.data;
};

export const deleteReport = async (reportId: number): Promise<void> => {
  await api.delete(`/v1/report/${reportId}`);
};
