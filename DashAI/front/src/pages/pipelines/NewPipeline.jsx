import React, { useRef, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Grid,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
import { ReactFlowProvider } from "reactflow";
import CustomLayout from "../../components/custom/CustomLayout";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import OptionBox from "../../components/threeSectionLayout/OptionBox";
import { Results as PipelineResults } from "../../components/pipelines";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { usePipelineState } from "../../hooks/usePipelineState";
import { useConnectedNodeData } from "../../hooks/useConnectedNodeData";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import {
  PipelineHeader,
  PipelineToolbar,
  PipelineDesigner,
  NodeSidebar,
  PipelineHistorySidebar,
  PipelineNodeConfigSidebar,
  nodeRegistry,
} from "../../components/pipelines";

const PIPELINE_TEMPLATES = [
  {
    id: "data_exploration",
    name: "Data Exploration",
    steps: ["DataSelector", "DataExploration"],
    labels: ["Data Selector", "Data Exploration"],
  },
  {
    id: "train_model",
    name: "Train Model",
    steps: [
      "DataSelector",
      "SplitData",
      "TaskAndModel",
      "MetricsEval",
      "Prediction",
    ],
    labels: [
      "Data Selector",
      "Split Data",
      "Task & Model",
      "Metrics",
      "Prediction",
    ],
  },
  {
    id: "retrieve_model",
    name: "Retrieve Model",
    steps: ["DataSelector", "RetrieveModel", "Prediction"],
    labels: ["Data Selector", "Retrieve Model", "Prediction"],
  },
];

function NewPipeline() {
  const theme = useTheme();
  const location = useLocation();
  const { pipelineId } = useParams();
  const navigate = useNavigate();
  const isNewPipelineRoute = location.pathname.endsWith("/new");
  const isWorkspaceOpen = Boolean(pipelineId) || isNewPipelineRoute;
  const flowWrapperRef = useRef(null);
  const [canvasMode, setCanvasMode] = useState("dark");
  const [centerMenuView, setCenterMenuView] = useState("home");
  const threePanelLayout = useThreePanelLayout({
    initialLeftWidth: 20,
    initialRightWidth: 20,
    overlayRightOnCompact: true,
    compactBreakpoint: "md",
  });

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
    isRunning,

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
    handleConnect,
    handleEdgeRemove,
    handlePipelineNameChange,
  } = usePipelineState(pipelineId, location, navigate);

  const { getConnectedNodeData } = useConnectedNodeData(nodes, nodeData, edges);

  const handleApplyTemplate = (templateId) => {
    const selectedTemplate = PIPELINE_TEMPLATES.find(
      (t) => t.id === templateId,
    );
    if (!selectedTemplate) return;

    if (!isWorkspaceOpen) {
      navigate("/app/pipelines/new", {
        state: { initialTemplateId: templateId },
      });
      return;
    }

    const startX = 120;
    const startY = 170;
    const spacingX = 230;

    const createdNodes = selectedTemplate.steps.map((nodeType, index) => {
      const nodeInfo = availableNodes.find((node) => node.type === nodeType);
      const nodeId = `${nodeType}-${index}`;

      return {
        id: nodeId,
        type: nodeType,
        position: {
          x: startX + index * spacingX,
          y: startY,
        },
        data: {
          label: nodeInfo?.name || nodeType,
          source: nodeInfo?.source || false,
          target: nodeInfo?.target || false,
          sourceHandles: nodeInfo?.sourceHandles || 1,
          targetHandles: nodeInfo?.targetHandles || 1,
          canvasMode,
          onDelete: () => {
            setNodes((nds) => nds.filter((n) => n.id !== nodeId));
            setNodeData((prev) => {
              const newData = { ...prev };
              delete newData[nodeId];
              return newData;
            });
            setEdges((eds) =>
              eds.filter(
                (edge) => edge.source !== nodeId && edge.target !== nodeId,
              ),
            );
          },
        },
        sourcePosition: "right",
        targetPosition: "left",
      };
    });

    const createdEdges = createdNodes.slice(0, -1).map((node, index) => ({
      id: `e-${node.id}-${createdNodes[index + 1].id}`,
      source: node.id,
      target: createdNodes[index + 1].id,
      markerEnd: {
        type: "arrowclosed",
      },
    }));

    setSelectedNode(null);
    setDragging(null);
    setNodeHelp(null);
    setHoveredNode(null);
    setValidationErrors({});
    setResultId(null);
    setNodeData({});
    setNodes(createdNodes);
    setEdges(createdEdges);
    setNodeIdCounter(createdNodes.length);
    setActiveTab("flow");
  };

  React.useEffect(() => {
    const templateIdFromState = location.state?.initialTemplateId;

    if (templateIdFromState && isWorkspaceOpen && availableNodes.length > 0) {
      handleApplyTemplate(templateIdFromState);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [
    availableNodes.length,
    isWorkspaceOpen,
    location.pathname,
    location.state,
    navigate,
  ]);

  React.useEffect(() => {
    if (isWorkspaceOpen) {
      setCenterMenuView("home");
    }
  }, [isWorkspaceOpen]);

  const handleNodeConfigOpen = (event, node) => {
    if (!threePanelLayout.rightBarVisible) {
      threePanelLayout.handleToggleRight();
    }
    onNodeClick(event, node);
  };

  const renderNodeConfigContent = () => {
    if (activeTab !== "flow") {
      return (
        <Typography variant="body2" color="text.secondary">
          Switch to the Flow tab to configure nodes.
        </Typography>
      );
    }

    if (!selectedNode) return null;

    const { type, id, data } = selectedNode;
    const { configType, configSchema } = data;
    let NodeComponent = null;

    if (configType === "custom") {
      NodeComponent = nodeRegistry[type];
    } else if (configType === "generic") {
      NodeComponent = nodeRegistry["Configurable"];
    }

    if (!NodeComponent) {
      return (
        <Typography variant="body2" color="text.secondary">
          This node does not require configuration.
        </Typography>
      );
    }

    return (
      <NodeComponent
        open={!!selectedNode}
        displayMode="panel"
        onClose={handleCloseDialog}
        onSave={(data) => handleSaveNodeData(id, data)}
        savedConfig={nodeData[id]}
        prevNodes={getConnectedNodeData(selectedNode)}
        configSchema={configSchema}
      />
    );
  };

  return (
    <CustomLayout disableContainer>
      <ReactFlowProvider>
        <ThreePanelLayoutContext.Provider value={threePanelLayout}>
          <ModuleContainer>
            <LeftPanel>
              <PipelineHistorySidebar currentPipelineId={pipelineId} />
            </LeftPanel>

            <CenterPanel>
              {!isWorkspaceOpen ? (
                <Box
                  sx={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                    justifyContent: "flex-start",
                    textAlign: "left",
                    px: { xs: 3, md: 4 },
                    py: { xs: 3, md: 4 },
                  }}
                >
                  {centerMenuView === "home" ? (
                    <>
                      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
                        Pipelines Module
                      </Typography>
                      <Typography
                        variant="h6"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        Create and manage your pipelines.
                      </Typography>

                      <Grid container spacing={1} sx={{ width: "100%", mt: 1 }}>
                        <Grid size={{ xs: 12, md: 6 }}>
                          <OptionBox
                            optionName="Create Empty Pipeline"
                            description="Start with an empty canvas and build your pipeline from scratch."
                            onClick={() => navigate("/app/pipelines/new")}
                          />
                        </Grid>
                        <Grid size={{ xs: 12, md: 6 }}>
                          <OptionBox
                            optionName="Choose a Prefabricated Pipeline"
                            description="Select a prefabricated pipeline and continue editing with your own data."
                            onClick={() => setCenterMenuView("prefabricated")}
                          />
                        </Grid>
                      </Grid>
                    </>
                  ) : (
                    <>
                      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
                        Choose a Prefabricated Pipeline
                      </Typography>
                      <Typography
                        variant="h6"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        Select one of the templates to open it in the workspace.
                      </Typography>

                      <Grid container spacing={1} sx={{ width: "100%", mt: 1 }}>
                        {PIPELINE_TEMPLATES.map((template) => (
                          <Grid size={{ xs: 12, md: 6 }} key={template.id}>
                            <Card
                              variant="outlined"
                              sx={{ cursor: "pointer", height: "100%" }}
                              onClick={() => handleApplyTemplate(template.id)}
                            >
                              <CardContent sx={{ pb: 1 }}>
                                <Typography variant="subtitle2" gutterBottom>
                                  {template.name}
                                </Typography>
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{ mb: 1.5 }}
                                >
                                  {(template.labels || template.steps).join(
                                    " + ",
                                  )}
                                </Typography>
                                <Box
                                  sx={{
                                    display: "flex",
                                    gap: 0.5,
                                    flexWrap: "wrap",
                                  }}
                                >
                                  {(template.labels || template.steps).map(
                                    (step) => (
                                      <Chip
                                        size="small"
                                        label={step}
                                        key={step}
                                      />
                                    ),
                                  )}
                                </Box>
                              </CardContent>
                              <CardActions sx={{ px: 2, pb: 1.5, pt: 0 }}>
                                <Button
                                  size="small"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    handleApplyTemplate(template.id);
                                  }}
                                >
                                  Use template
                                </Button>
                              </CardActions>
                            </Card>
                          </Grid>
                        ))}
                      </Grid>

                      <Box
                        sx={{
                          width: "100%",
                          display: "flex",
                          justifyContent: "flex-end",
                          mt: 3,
                        }}
                      >
                        <Button
                          variant="outlined"
                          onClick={() => setCenterMenuView("home")}
                        >
                          ATRAS
                        </Button>
                      </Box>
                    </>
                  )}
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    minHeight: "100%",
                  }}
                >
                  <Box sx={{ px: 2, pt: 1, pb: 1 }}>
                    <PipelineHeader
                      activeTab={activeTab}
                      setActiveTab={setActiveTab}
                      navigate={navigate}
                    />
                  </Box>

                  {activeTab === "flow" ? (
                    <Box
                      sx={{
                        display: "flex",
                        minHeight: 0,
                        flex: 1,
                        borderRadius: 1,
                        overflow: "hidden",
                        border: `1px solid ${theme.palette.ui.borderLight}`,
                      }}
                    >
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
                          minWidth: 0,
                          minHeight: 0,
                          display: "flex",
                          flexDirection: "column",
                        }}
                      >
                        <PipelineToolbar
                          pipelineName={pipelineName}
                          setPipelineName={setPipelineName}
                          onRun={handleRun}
                          nameError={nameError}
                          nameErrorMessage={nameErrorMessage}
                          handlePipelineNameChange={handlePipelineNameChange}
                          canvasMode={canvasMode}
                          setCanvasMode={setCanvasMode}
                          isRunning={isRunning}
                        />

                        <PipelineDesigner
                          nodes={nodes}
                          setNodes={setNodes}
                          edges={edges}
                          setEdges={setEdges}
                          onNodesChange={onNodesChange}
                          onEdgesChange={onEdgesChange}
                          onConnect={handleConnect}
                          onEdgeDoubleClick={handleEdgeRemove}
                          nodeTypes={nodeTypes}
                          onNodeClick={handleNodeConfigOpen}
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
                          canvasMode={canvasMode}
                        />
                      </Box>
                    </Box>
                  ) : (
                    <Box sx={{ p: 2, flex: 1 }}>
                      {resultId ? (
                        <PipelineResults pipelineId={resultId} />
                      ) : (
                        <Typography>No results yet.</Typography>
                      )}
                    </Box>
                  )}
                </Box>
              )}
            </CenterPanel>

            <RightPanel toggleButtonTop="50%">
              <PipelineNodeConfigSidebar
                selectedNode={selectedNode}
                onClose={handleCloseDialog}
              >
                {renderNodeConfigContent()}
              </PipelineNodeConfigSidebar>
            </RightPanel>
          </ModuleContainer>
        </ThreePanelLayoutContext.Provider>
      </ReactFlowProvider>
    </CustomLayout>
  );
}

export default NewPipeline;
