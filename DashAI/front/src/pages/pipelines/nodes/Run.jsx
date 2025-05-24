import React from "react";
import { createPipeline } from "../../../api/pipeline";
import { enqueuePipelineJob, startJobQueue } from "../../../api/job";

async function RunPipeline(nodes, nodeData, name, edges, enqueueSnackbar) {
  const steps = nodes.map((node) => {
    const config = nodeData[node.id] || {};

    return {
      id: node.id,
      type: node.type,
      label: node.data.label,
      config: config,
    };
  });

  const formData = {
    name: name,
    steps: steps,
    edges: edges,
    exploration: null,
    train: null,
    prediction: null,
  };

  try {
    const response = await createPipeline(formData);
    enqueueSnackbar("Pipeline saved successfully.", { variant: "success" });
    await enqueuePipelineJob(response.id);
    enqueueSnackbar("Pipeline job enqueued successfully.", { variant: "info" });
    await startJobQueue();
    return response.id;
  } catch (error) {
    console.error("Error saving pipeline:", error);
    enqueueSnackbar("Failed to save pipeline.", { variant: "error" });
    return null;
  }
}

export default RunPipeline;
