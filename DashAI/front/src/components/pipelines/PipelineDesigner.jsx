import React, { useCallback } from "react";
import { Box, Tooltip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";

function PipelineDesigner({
  nodes,
  setNodes,
  edges,
  setEdges,
  onNodesChange,
  onEdgesChange,
  nodeTypes,
  onNodeClick,
  onNodeHelp,
  onNodeMouseEnter,
  onNodeMouseLeave,
  onPaneClick,
  validationErrors,
  hoveredNode,
  flowWrapperRef,
  dragging,
  nodeData,
  setNodeData,
  nodeIdCounter,
  setNodeIdCounter,
  availableNodes,
}) {
  const theme = useTheme();
  const { screenToFlowPosition } = useReactFlow();

  const onConnect = (params) => {
    setEdges((eds) =>
      addEdge(
        {
          ...params,
          markerEnd: {
            type: "arrowclosed",
          },
        },
        eds,
      ),
    );
  };

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      if (!dragging) {
        return;
      }

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeId = `${dragging}-${nodeIdCounter}`;
      const nodeErrors = validationErrors[nodeId] ?? [];

      // Get node info from availableNodes to set source/target properties
      const nodeInfo = availableNodes.find((n) => n.type === dragging);

      const newNode = {
        id: nodeId,
        type: dragging,
        position,
        data: {
          label: dragging,
          hasError: validationErrors[nodeId],
          errors: nodeErrors,
          source: nodeInfo?.source || false,
          target: nodeInfo?.target || false,
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
      availableNodes,
    ],
  );

  return (
    <Box sx={{ width: "100%", height: "73vh" }} ref={flowWrapperRef}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeClick={onNodeHelp}
        onPaneClick={onPaneClick}
        onNodeDoubleClick={onNodeClick}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        nodeTypes={nodeTypes}
        fitView
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 12,
          background: theme.palette.background.default,
          border: `1px solid ${theme.palette.ui.border}`,
          boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
        }}
      >
        {hoveredNode && (
          <Tooltip
            open
            title={
              Array.isArray(validationErrors[hoveredNode.id])
                ? validationErrors[hoveredNode.id].join("\n")
                : String(validationErrors[hoveredNode.id]).replace(
                    /\. /g,
                    ".\n",
                  )
            }
            placement="top"
            slotProps={{
              tooltip: {
                sx: {
                  fontSize: "15px",
                  whiteSpace: "pre-line",
                },
              },
            }}
          >
            <div />
          </Tooltip>
        )}
        <Controls />
        <Background />
      </ReactFlow>
    </Box>
  );
}

export default PipelineDesigner;
