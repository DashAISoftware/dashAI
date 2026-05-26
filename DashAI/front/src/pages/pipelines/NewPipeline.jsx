import React, { useRef } from "react";
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
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
  const theme = useTheme();
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
    nameError,
    nameErrorMessage,

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
    handlePipelineNameChange,
  } = usePipelineState(pipelineId, location, navigate);

  const { getConnectedNodeData } = useConnectedNodeData(nodes, nodeData, edges);

  const renderNodeDialogContent = () => {
    if (!selectedNode) return null;

    const { type, id, data } = selectedNode;
    const { configType, configSchema } = data;
    let NodeComponent = null;

    if (configType === "custom") {
      NodeComponent = nodeRegistry[type];
    } else if (configType === "generic") {
      NodeComponent = nodeRegistry["Configurable"];
    }

    if (!NodeComponent) return null;

    return (
      <NodeComponent
        open={!!selectedNode}
        onClose={handleCloseDialog}
        onSave={(data) => handleSaveNodeData(id, data)}
        savedConfig={nodeData[id]}
        prevNodes={getConnectedNodeData(selectedNode)}
        configSchema={configSchema}
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

              <Box
                sx={{
                  flexGrow: 1,
                  p: 2,
                  backgroundColor: theme.palette.background.default,
                }}
              >
                <PipelineToolbar
                  pipelineName={pipelineName}
                  setPipelineName={setPipelineName}
                  onRun={handleRun}
                  nameError={nameError}
                  nameErrorMessage={nameErrorMessage}
                  handlePipelineNameChange={handlePipelineNameChange}
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
                <Dialog
                  open={true}
                  onClose={() => {}}
                  disableEscapeKeyDown
                  maxWidth="md"
                  fullWidth
                >
                  <DialogTitle>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Typography variant="h6">
                        {selectedNode?.type === "Train"
                          ? "Select Train Parameters"
                          : selectedNode?.type === "Exploration"
                            ? "Exploration Configuration"
                            : `Configure ${selectedNode?.type || "Node"}`}
                      </Typography>
                      <IconButton
                        onClick={handleCloseDialog}
                        sx={{ position: "absolute", right: 8, top: 8 }}
                      >
                        <CloseIcon />
                      </IconButton>
                    </Box>
                  </DialogTitle>
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
