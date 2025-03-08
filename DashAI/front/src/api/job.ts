import api from "./api";

export const getJobs = async (): Promise<object> => {
  const response = await api.get<object>("/v1/job/");
  return response.data;
};

export const enqueueRunnerJob = async (runId: number): Promise<object> => {
  const data = {
    job_type: "ModelJob",
    kwargs: { run_id: runId },
  };
  const formData = new FormData();
  formData.append("job_type", data.job_type);
  formData.append("kwargs", JSON.stringify(data.kwargs));
  const response = await api.post<object>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const enqueueDatasetJob = async (
  file: File,
  name: string,
  url: string,
  params: object,
): Promise<object> => {
  const formData = new FormData();
  const kwargs = {
    name: name,
    url: url,
    params: params,
  };

  formData.append("job_type", "DatasetJob");
  formData.append("kwargs", JSON.stringify(kwargs));
  formData.append("file", file);

  const response = await api.post<object>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      filename: encodeURIComponent(file.name),
    },
  });
  return response.data;
};

export const enqueueExplainerJob = async (
  explainerId: number,
  scope: string,
): Promise<object> => {
  const data = {
    job_type: "ExplainerJob",
    kwargs: { explainer_id: explainerId, explainer_scope: scope },
  };

  const formData = new FormData();
  formData.append("job_type", data.job_type);
  formData.append("kwargs", JSON.stringify(data.kwargs));

  const response = await api.post<object>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const enqueuePredictionJob = async (
  run_id: number,
  id: number,
  json_filename: string,
): Promise<object> => {
  const data = {
    job_type: "PredictJob",
    kwargs: { run_id, id, json_filename },
  };

  const formData = new FormData();
  formData.append("job_type", data.job_type);
  formData.append("kwargs", JSON.stringify(data.kwargs));

  const response = await api.post<object>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const enqueueConverterJob = async (
  converterListId: number,
  targetColumnIndex: number,
): Promise<object> => {
  const data = {
    job_type: "ConverterListJob",
    kwargs: {
      converter_list_id: converterListId,
      target_column_index: targetColumnIndex,
    },
  };

  const response = await api.post<object>("/v1/job/", data);
  return response.data;
};

export const enqueueExplorerJob = async (
  explorerId: number,
): Promise<object> => {
  const data = {
    job_type: "ExplorerJob",
    kwargs: { explorer_id: explorerId },
  };

  const response = await api.post<object>("/v1/job/", data);
  return response.data;
};

export const startJobQueue = async (
  stopWhenQueueEmpties: boolean | undefined,
): Promise<object> => {
  let params = {};

  if (stopWhenQueueEmpties !== undefined) {
    params = { ...params, stop_when_queue_empties: stopWhenQueueEmpties };
  }

  const response = await api.post<object>("/v1/job/start/", null, { params });
  return response.data;
};
