let nodeHelp = {
  Pipeline: {
    description: `Design a machine learning workflow by dragging and connecting nodes.
    Single-click a node to see more information.
    Double-click a node to configure parameters.
    Double-click an edge to remove the connection.`,
  },
};

export function buildNodeHelp(nodeInfo) {
  nodeInfo.forEach((node) => {
    nodeHelp[node.type] = {
      name: node.name,
      description: node.description || "No description available.",
      input: node.input,
      output: node.output,
      next: node.next?.join(", ") || "",
    };
  });
}

export function getNodeHelp(nodeType) {
  return (
    nodeHelp[nodeType] || {
      description: "No description available.",
    }
  );
}
