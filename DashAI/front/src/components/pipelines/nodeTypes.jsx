import { getNodeContracts } from "../../api/pipeline";
import CustomNode from "./CustomNode";

export async function getNodeTypes() {
  try {
    const response = await getNodeContracts();
    if (Array.isArray(response)) {
      return response;
    } else {
      return [];
    }
  } catch (error) {
    console.error("Error fetching node types:", error);
    return [];
  }
}

export async function getNodeTypesMap() {
  const nodeDefinitions = await getNodeTypes();
  const nodeTypes = {};

  nodeDefinitions.forEach((node) => {
    nodeTypes[node.type] = CustomNode;
  });

  return nodeTypes;
}
