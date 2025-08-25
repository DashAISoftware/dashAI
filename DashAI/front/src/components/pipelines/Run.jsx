import { createPipeline, updatePipeline } from "../../api/pipeline";
import { enqueuePipelineJob, startJobQueue } from "../../api/job";

async function RunPipeline(
  nodes,
  nodeData,
  name,
  edges,
  enqueueSnackbar,
  pipelineId = null,
) {
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
    if (pipelineId) {
      await updatePipeline(pipelineId, formData);
      enqueueSnackbar("Pipeline updated successfully.", { variant: "success" });
      await enqueuePipelineJob(pipelineId);
      await startJobQueue();
      return pipelineId;
    } else {
      const newPipeline = await createPipeline(formData);
      enqueueSnackbar("Pipeline created successfully.", { variant: "success" });
      await enqueuePipelineJob(newPipeline.id);
      await startJobQueue();
      return newPipeline.id;
    }
  } catch (error) {
    console.error("Error saving pipeline:", error);
    enqueueSnackbar("Failed to save pipeline.", { variant: "error" });
    return null;
  }
}

export default RunPipeline;
