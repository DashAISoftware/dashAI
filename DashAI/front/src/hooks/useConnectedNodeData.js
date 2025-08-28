import { useCallback } from "react";

export function useConnectedNodeData(nodes, nodeData, edges) {
  const getConnectedNodeData = useCallback(
    (selectedNode) => {
      const visited = new Set();
      const result = [];

      function traverseBackwards(nodeId) {
        if (visited.has(nodeId)) return;
        visited.add(nodeId);
        const node = nodes.find((n) => n.id === nodeId);
        if (node && nodeData[nodeId]) {
          result.push(nodeData[nodeId]);
        }
        const incomingEdges = edges.filter((edge) => edge.target === nodeId);
        for (const edge of incomingEdges) {
          traverseBackwards(edge.source);
        }
      }

      traverseBackwards(selectedNode.id);
      return result;
    },
    [nodes, nodeData, edges],
  );

  return { getConnectedNodeData };
}
