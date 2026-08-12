import api from "./api";

export interface IInsightResult {
  id: number;
  status: string;
  result_text: string | null;
  error_message: string | null;
}

export const createExplainerInsight = async (
  scope: string,
  explainerId: number,
  artifactTitle: string,
  modelName: string,
  language: string = "en",
): Promise<{ id: string; insight_result_id: number }> => {
  const response = await api.post(
    `/v1/insight/explainer/${scope}/${explainerId}`,
    {
      artifact_title: artifactTitle,
      provider_kind: "local",
      provider_params: { model_name: modelName },
      language,
    },
  );
  return response.data;
};

export const getInsight = async (
  insightResultId: number,
): Promise<IInsightResult> => {
  const response = await api.get<IInsightResult>(
    `/v1/insight/${insightResultId}`,
  );
  return response.data;
};

export interface ILatestInsight {
  insight_result_id: number | null;
  status: string | null;
  result_text: string | null;
  error_message: string | null;
  huey_id: string | null;
}

export const getLatestExplainerInsight = async (
  scope: string,
  explainerId: number,
  artifactTitle: string,
): Promise<ILatestInsight> => {
  const response = await api.get<ILatestInsight>(
    `/v1/insight/explainer/${scope}/${explainerId}/latest`,
    { params: { artifact_title: artifactTitle } },
  );
  return response.data;
};
