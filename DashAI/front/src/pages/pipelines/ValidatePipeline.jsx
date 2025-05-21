function buildGraph(nodes, edges) {
  const graph = {};
  const inDegree = {};

  nodes.forEach(node => {
    graph[node.id] = [];
    inDegree[node.id] = 0;
  });

  edges.forEach(edge => {
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
  console.log("Execution order:", order);
  return order;
}

function sortNodes(nodes, edges) {
  const { graph, inDegree } = buildGraph(nodes, edges);
  const order = getExecutionOrder(graph, { ...inDegree });

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
  const orderedNodes = order.map(id => nodeMap[id]).filter(Boolean);

  return orderedNodes;
}

function validatePipeline(nodes, edges) {
  const { graph, inDegree } = buildGraph(nodes, edges);
  const executionOrder = getExecutionOrder(graph, { ...inDegree });
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));

  const errors = {};
  const addError = (nodeId, msg) => {
    if (!errors[nodeId]) {
      errors[nodeId] = [];
    }
    errors[nodeId].push(msg);
  };

  const typeToNodes = {};
  const duplicatedNodeIds = new Set();

  nodes.forEach(node => {
    if (!typeToNodes[node.type]) {
      typeToNodes[node.type] = [];
    }
    typeToNodes[node.type].push(node.id);
  });

  Object.entries(typeToNodes).forEach(([type, ids]) => {
    if (ids.length > 1) {
      ids.slice(1).forEach(id => {
        duplicatedNodeIds.add(id);
        addError(id, `${type} already exists.`);
      });
    }
  });

  executionOrder.forEach(nodeId => {
    if (duplicatedNodeIds.has(nodeId)) {
      return;
    }

    const node = nodeMap[nodeId];
    const predecessors = edges.filter(e => e.target === nodeId).map(e => nodeMap[e.source]?.type);
    const successors = edges.filter(e => e.source === nodeId).map(e => nodeMap[e.target]?.type);

    const predecessorIds = edges.filter(e => e.target === nodeId).map(e => e.source);
    const successorIds = edges.filter(e => e.source === nodeId).map(e => e.target);

    if (node.type === "DataSelector") {
      if (predecessorIds.length > 0) {
        addError(nodeId, "DataSelector should not have any inputs.");
      }
      if (successorIds.length > 0) {
        if (!successors.every(t => ["DataExploration", "Train"].includes(t))) {
          addError(nodeId, "DataSelector can only connect to DataExploration or Train Node.");
        }
      }
    }

    if (node.type === "DataExploration") {
      if (!predecessors.includes("DataSelector")) {
        addError(nodeId, "DataExploration must be connected to a DataSelector Node.");
      }
    }

    if (node.type === "Train") {
      if (!predecessors.some(t => t === "DataSelector" || t === "DataExploration")) {
        addError(nodeId, "Train must be connected to a DataSelector Node.");
      }
    }

    if (node.type === "Prediction") {
      if (predecessors.length !== 1 || predecessors[0] !== "Train") {
        addError(nodeId, "Prediction must be connected to a Train Node.");
      }
      if (successorIds.length > 0) {
        addError(nodeId, "Prediction should not have any outputs.");
      }
    }
  });

  console.log(errors)
  return errors;
}

export { sortNodes, validatePipeline };
