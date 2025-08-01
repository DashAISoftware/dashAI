import React, { useRef } from "react";
import { Box, Typography, Dialog } from "@mui/material";
import { ReactFlowProvider } from "reactflow";
import CustomLayout from "../../components/custom/CustomLayout";
import { Results as PipelineResults } from "../../components/pipelines";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { usePipelineState } from "../../hooks/usePipelineState";
import { useConnectedNodeData } from "../../hooks/useConnectedNodeData";
import {
  PipelineHeader,
  PipelineToolbar,
  PipelineDesigner,
  NodeSidebar,
  nodeRegistry,
} from "../../components/pipelines";

function NewPipeline() {
  const location = useLocation();
  const { pipelineId } = useParams();
  const navigate = useNavigate();
  const flowWrapperRef = useRef(null);

  const {
    // State
    nodes,
    edges,
    selectedNode,
    dragging,
    nodeData,
    activeTab,
    resultId,
    pipelineName,
    validationErrors,
    hoveredNode,
    nodeHelp,
    availableNodes,
    nodeTypes,
    nodeIdCounter,

    // Setters
    setNodes,
    setEdges,
    setSelectedNode,
    setDragging,
    setNodeData,
    setActiveTab,
    setResultId,
    setPipelineName,
    setValidationErrors,
    setHoveredNode,
    setNodeHelp,
    setNodeIdCounter,

    // Event handlers
    onNodesChange,
    onEdgesChange,
    onDragStart,
    handleCloseDialog,
    handleSaveNodeData,
    handleRun,
    onNodeClick,
    onNodeHelp,
    onNodeMouseEnter,
    onNodeMouseLeave,
    onPaneClick,
  } = usePipelineState(pipelineId, location, navigate);

  const { getConnectedNodeData } = useConnectedNodeData(nodes, nodeData, edges);

  const renderNodeDialogContent = () => {
    if (!selectedNode) return null;
    const { type, id } = selectedNode;
    const NodeComponent = nodeRegistry[type];
    if (!NodeComponent) return null;

    return (
      <NodeComponent
        open={!!selectedNode}
        onClose={handleCloseDialog}
        onSave={(data) => handleSaveNodeData(id, data)}
        savedConfig={nodeData[id]}
        prevNodes={getConnectedNodeData(selectedNode)}
      />
    );
  };

  return (
    <CustomLayout
      title="Pipelines Module"
      subtitle="Create and manage your pipelines."
    >
      <ReactFlowProvider>
        <PipelineHeader
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          navigate={navigate}
        />

        {activeTab === "flow" ? (
          <>
            <Box display="flex" height="85vh">
              <NodeSidebar
                availableNodes={availableNodes}
                onDragStart={onDragStart}
                nodeHelp={nodeHelp}
              />

              <Box sx={{ flexGrow: 1, p: 2, backgroundColor: "#f5f5f5" }}>
                <PipelineToolbar
                  pipelineName={pipelineName}
                  setPipelineName={setPipelineName}
                  onRun={handleRun}
                />

                <PipelineDesigner
                  nodes={nodes}
                  setNodes={setNodes}
                  edges={edges}
                  setEdges={setEdges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  nodeTypes={nodeTypes}
                  onNodeClick={onNodeClick}
                  onNodeHelp={onNodeHelp}
                  onNodeMouseEnter={onNodeMouseEnter}
                  onNodeMouseLeave={onNodeMouseLeave}
                  onPaneClick={onPaneClick}
                  validationErrors={validationErrors}
                  hoveredNode={hoveredNode}
                  flowWrapperRef={flowWrapperRef}
                  dragging={dragging}
                  nodeData={nodeData}
                  setNodeData={setNodeData}
                  nodeIdCounter={nodeIdCounter}
                  setNodeIdCounter={setNodeIdCounter}
                  availableNodes={availableNodes}
                />
              </Box>

              {renderNodeDialogContent() && (
                <Dialog open={true} onClose={handleCloseDialog}>
                  {renderNodeDialogContent()}
                </Dialog>
              )}
            </Box>
          </>
        ) : (
          <Box sx={{ p: 2 }}>
            {resultId ? (
              <PipelineResults pipelineId={resultId} />
            ) : (
              <Typography>No results yet.</Typography>
            )}
          </Box>
        )}
      </ReactFlowProvider>
    </CustomLayout>
  );
}

export default NewPipeline;
