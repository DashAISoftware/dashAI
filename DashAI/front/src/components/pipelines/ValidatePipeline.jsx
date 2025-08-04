import { validatePipeline as pipelineValidator } from "../../api/pipeline";

function buildGraph(nodes, edges) {
  const graph = {};
  const inDegree = {};

  nodes.forEach((node) => {
    graph[node.id] = [];
    inDegree[node.id] = 0;
  });

  edges.forEach((edge) => {
    graph[edge.source].push(edge.target);
    inDegree[edge.target]++;
  });

  return { graph, inDegree };
}

function getExecutionOrder(graph, inDegree) {
  const queue = [];
  const order = [];

  for (const nodeId in inDegree) {
    if (inDegree[nodeId] === 0) {
      queue.push(nodeId);
    }
  }

  while (queue.length > 0) {
    const current = queue.shift();
    order.push(current);

    for (const neighbor of graph[current]) {
      inDegree[neighbor]--;
      if (inDegree[neighbor] === 0) {
        queue.push(neighbor);
      }
    }
  }
  return order;
}

function sortNodes(nodes, edges) {
  const { graph, inDegree } = buildGraph(nodes, edges);
  const order = getExecutionOrder(graph, { ...inDegree });

  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const orderedNodes = order.map((id) => nodeMap[id]).filter(Boolean);

  return orderedNodes;
}

async function validatePipeline(nodes, edges) {
  const { graph, inDegree } = buildGraph(nodes, edges);
  const executionOrder = getExecutionOrder(graph, { ...inDegree });

  const orderedNodes = executionOrder.map((id) =>
    nodes.find((n) => n.id === id),
  );

  try {
    const response = await pipelineValidator(orderedNodes, edges);
    return response || {};
  } catch (error) {
    console.error("Pipeline validation error:", error);
    return { general: ["Error validating pipeline structure."] };
  }
}

export { sortNodes, validatePipeline, buildGraph, getExecutionOrder };
