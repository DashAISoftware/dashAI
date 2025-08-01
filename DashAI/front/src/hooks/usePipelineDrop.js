import { useCallback } from "react";
import { useReactFlow } from "reactflow";

export function usePipelineDrop(
  dragging,
  setNodes,
  setNodeData,
  setEdges,
  validationErrors,
  nodeIdCounter,
  setNodeIdCounter,
) {
  const { screenToFlowPosition } = useReactFlow();

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeId = `${dragging}-${nodeIdCounter}`;
      const nodeErrors = validationErrors[nodeId] ?? [];

      const newNode = {
        id: nodeId,
        type: dragging,
        position,
        data: {
          label: dragging,
          hasError: validationErrors[nodeId],
          errors: nodeErrors,
          onDelete: () => {
            setNodes((nds) => nds.filter((n) => n.id !== nodeId));
            setNodeData((prev) => {
              const newData = { ...prev };
              delete newData[nodeId];
              return newData;
            });
            setEdges((eds) =>
              eds.filter((e) => e.source !== nodeId && e.target !== nodeId),
            );
          },
        },
        sourcePosition: "right",
        targetPosition: "left",
      };

      setNodes((nds) => nds.concat(newNode));
      setNodeIdCounter((prev) => prev + 1);
    },
    [
      dragging,
      setNodes,
      setNodeData,
      setEdges,
      screenToFlowPosition,
      validationErrors,
      nodeIdCounter,
      setNodeIdCounter,
    ],
  );

  return { onDrop };
}
