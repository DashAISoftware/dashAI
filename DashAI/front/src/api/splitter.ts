import api from "./api";

const splitterEndpoint = "/v1/splitter";

export interface ISplitPreviewSegment {
  role: "train" | "validation" | "test" | "unused";
  fraction: number;
}

// A bar of the preview, or an ellipsis standing for the bars left out. The
// labels and notes are keys of the experiments:splitPreview translations.
export interface ISplitPreviewRow {
  key: string;
  label: string;
  label_values?: Record<string, unknown>;
  segments?: ISplitPreviewSegment[];
  ellipsis?: boolean;
  hidden_count?: number;
}

export interface ISplitPreviewMessage {
  key: string;
  values: Record<string, unknown>;
}

export interface ISplitPreview {
  rows: ISplitPreviewRow[];
  notes: ISplitPreviewMessage[];
  shares: Record<string, number>;
  // What keeps the configuration from being used, as experiments:error keys.
  errors: ISplitPreviewMessage[];
  // The partitions that receive rows, which pick the metrics a session records.
  partitions: string[];
}

export interface ISplitPreviewRequest {
  datasetId: number;
  splitterName: string;
  params: Record<string, unknown>;
  splitType?: string | null;
  indexes?: Record<string, number[]> | null;
}

// How a splitter would carve a dataset, computed by the splitter itself. Null
// for a splitter that does not describe its shape.
export const previewSplit = async ({
  datasetId,
  splitterName,
  params,
  splitType = null,
  indexes = null,
}: ISplitPreviewRequest): Promise<ISplitPreview | null> => {
  const response = await api.post<ISplitPreview | null>(
    `${splitterEndpoint}/preview`,
    {
      dataset_id: datasetId,
      splitter_name: splitterName,
      params: params ?? {},
      split_type: splitType,
      indexes,
    },
  );
  return response.data;
};
