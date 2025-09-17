import api from "./api";

export const isQueueEmpty = async (): Promise<boolean> => {
  const response = await api.get<{ is_empty: boolean }>("/v1/job/is_empty");
  return response.data.is_empty;
};

export const getJobs = async (): Promise<object> => {
  const response = await api.get<object>("/v1/job/");
  return response.data;
};

export const getJobChanges = async (
  since: string,
): Promise<{
  jobs: any[];
  cursor: string;
  server_now: string;
  queue_empty: boolean;
  recently_completed: boolean;
}> => {
  const response = await api.get<any>("/v1/job/changes", {
    params: { since },
  });
  return response.data;
};

export const getJobDetails = async (jobId: string): Promise<object> => {
  const response = await api.get<object>(`/v1/job/${jobId}/details`);
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<any> => {
  const response = await api.get<any>(`/v1/job/status/${jobId}`);
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

export const enqueueExplorerJob = async (
  explorerId: number,
): Promise<object> => {
  const formData = new FormData();
  const kwargs = {
    explorer_id: explorerId,
  };

  formData.append("job_type", "ExplorerJob");
  formData.append("stop_when_queue_empties", JSON.stringify(true));
  formData.append("kwargs", JSON.stringify(kwargs));

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

export const enqueueGenerativeProcessJob = async (
  processId: number,
): Promise<object> => {
  const data = {
    job_type: "GenerativeJob",
    kwargs: { generative_process_id: processId },
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
): Promise<object> => {
  const data = {
    job_type: "ConverterListJob",
    kwargs: {
      converter_list_id: converterListId,
    },
    stop_when_queue_empties: true,
  };

  const formData = new FormData();
  formData.append("job_type", data.job_type);
  formData.append(
    "stop_when_queue_empties",
    JSON.stringify(data.stop_when_queue_empties),
  );
  formData.append("kwargs", JSON.stringify(data.kwargs));

  const response = await api.post<object>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// export const startJobQueue = async (
//   stopWhenQueueEmpties: boolean | undefined,
// ): Promise<object> => {
//   let params = {};

//   if (stopWhenQueueEmpties !== undefined) {
//     params = { ...params, stop_when_queue_empties: stopWhenQueueEmpties };
//   }

//   const response = await api.post<object>("/v1/job/start/", null, { params });
//   return response.data;
// };
export const startJobQueue = async (
  stopWhenQueueEmpties?: boolean,
): Promise<void> => {
  return;
};

export const deleteJob = async (jobId: string): Promise<void> => {
  await api.delete(`/v1/job/${jobId}`);
};

export const deleteAllJobs = async (): Promise<{ deleted: number }> => {
  const response = await api.delete<{ deleted: number }>("/v1/job/all");
  return response.data;
};

export const enqueuePipelineJob = async (
  pipelineId: number,
): Promise<object> => {
  const data = {
    job_type: "PipelineJob",
    kwargs: { id: pipelineId },
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
