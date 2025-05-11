import React, { useEffect } from "react";
import { createPipeline } from "../../../api/pipeline";

async function RunPipeline(nodes, nodeData) {
  const steps = nodes.map((node) => ({
    id: node.id,
    type: node.type,
    label: node.data.label,
    config: nodeData[node.id] || {},
  }));

  const formData = {
    steps: steps,
    exploration: null,
    train: null,
    prediction: null,
  };
  console.log(formData);

  try {
    const response = await createPipeline(formData);
    console.log("Pipeline saved successfully:", response);
    alert("Pipeline saved successfully!");
    return response.id;
  } catch (error) {
    console.error("Error saving pipeline:", error);
    alert("Failed to save pipeline. Check the console for details.");
    return null;
  }
}

export default RunPipeline;
