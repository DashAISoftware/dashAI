import React from "react";
import { createPipeline } from "../../../api/pipeline";

async function RunPipeline(nodes, nodeData, name, edges) {
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
