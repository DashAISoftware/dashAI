import React, { useState, useCallback, useEffect, useRef } from "react";
import { Box, Typography, Dialog, TextField, Button, Tooltip } from "@mui/material";
import ArrowBackIosIcon from '@mui/icons-material/ArrowBackIos';
import ReactFlow, { addEdge, Background, Controls, useEdgesState, useNodesState, useReactFlow } from "reactflow";
import 'reactflow/dist/style.css';
import CustomLayout from "../../components/custom/CustomLayout";
import RunPipeline from "./nodes/Run";
import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TrainNode from "./nodes/TrainNode";
import PredictionNode from "./nodes/PredictionNode";
import PipelineResults from "./Results";
import { getPipelineById, updatePipeline } from "../../api/pipeline";
import { useParams, useNavigate } from "react-router-dom";
import { useLocation } from "react-router-dom";
import CustomNode from "./CustomNode";
import { useSnackbar } from "notistack";
import { validatePipeline, sortNodes } from "./ValidatePipeline"
import { enqueuePipelineJob, startJobQueue } from "../../api/job";

const nodeTypes = {
  DataSelector: CustomNode,
  DataExploration: CustomNode,
  Train: CustomNode,
  Prediction: CustomNode,
};

function NewPipeline() {
  const location = useLocation();
  const { pipelineId } = useParams();
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [nodeData, setNodeData] = useState({});
  const [activeTab, setActiveTab] = useState(location.state?.activeTab || "flow");
  const [resultId, setResultId] = useState(null);
  const [pipelineName, setPipelineName] = useState("undefined");
  const [validationErrors, setValidationErrors] = useState({});
  const [hoveredNode, setHoveredNode] = useState(null);
  const flowWrapperRef = useRef(null);
  const { enqueueSnackbar } = useSnackbar();
  const { screenToFlowPosition } = useReactFlow();

  useEffect(() => {
    if (location.state?.activeTab) {
      setActiveTab(location.state.activeTab);
    }
  }, [location.state?.activeTab]);

  const onDragStart = (event, nodeType) => {
    setDragging(nodeType);
    event.dataTransfer.setData('text/plain', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);


  const onDrop = useCallback((event) => {
    event.preventDefault();
    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    const nodeId = `${dragging}-${nodes.length}`;
    const nodeErrors = validationErrors[nodeId] ?? [];
    
    const newNode = {
      id: nodeId, 
      type: dragging, 
      position,
      data: { label: dragging, hasError: validationErrors[nodeId], errors: nodeErrors },
      sourcePosition: "right",
      targetPosition: "left",
    };

    setNodes((nds) => nds.concat(newNode));
  }, [dragging, nodes.length, setNodes, screenToFlowPosition, validationErrors]);

  const requiresConfiguration = (type) => type !== "Prediction";

  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        const hasError = !!validationErrors[node.id];
        const needsConfig = requiresConfiguration(node.type);
        const isConfigured = nodeData[node.id] !== undefined;

        return {
          ...node,
          data: {
            ...node.data,
            hasError,
            notConfigured: needsConfig && !isConfigured,
            errors: validationErrors[node.id]
          },
        };
      })
    );
  }, [validationErrors, nodeData]);

  const onConnect = (params) => {
    setEdges((eds) => addEdge(
      {
        ...params,
        markerEnd: {
          type: 'arrowclosed',
        },
      },
      eds
    ));
  };

  useEffect(() => {
    if (pipelineId) {
      (async () => {
        const pipeline = await getPipelineById(pipelineId);
        const loadedNodes = pipeline.steps.map((step, idx) => ({
          id: step.id,
          type: step.type,
          position: { x: idx * 250, y: 100 },
          data: { label: step.label },
          sourcePosition: "right",
          targetPosition: "left",
        }));
        setNodes(loadedNodes);
        setEdges(pipeline.edges || []);
        const configMap = {};
        pipeline.steps.forEach(step => {
          configMap[step.id] = step.config;
        });
        setNodeData(configMap);
        setResultId(pipelineId);
        setPipelineName(pipeline.name);
      })();
    }
  }, [pipelineId]);

  const handleCloseDialog = () => {
    setSelectedNode(null);
  };

  const handleSaveNodeData = (nodeId, data) => {
    setNodeData((prev) => ({
      ...prev,
      [nodeId]: data,
    }));
    handleCloseDialog();
  };

  function buildSteps(nodes, nodeData) {
    return nodes.map(n => {
      const config = { ...nodeData[n.id] };
      return {
        id: n.id,
        type: n.type,
        label: n.data.label,
        config: config,
      };
    });
  }

  useEffect(() => {
    const errors = validatePipeline(nodes, edges);
    setValidationErrors(errors);

    setNodes((prevNodes) =>
      prevNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          hasError: !!errors[node.id],
        }
      }))
    );
  }, [nodes.length, edges]);

  const handleRun = async () => {
    const sortedNodes = sortNodes(nodes, edges);
    const errors = validatePipeline(sortedNodes, edges);
    if (Object.keys(errors).length > 0) {
      enqueueSnackbar("Error in pipeline", { variant: "error" });
      return;
    }
    let newId;
    if (pipelineId) {
      await updatePipeline(pipelineId, { name: pipelineName, steps: buildSteps(sortedNodes, nodeData), edges: edges });
      enqueueSnackbar("Pipeline updated successfully.", { variant: "success" });
      await enqueuePipelineJob(pipelineId);
      enqueueSnackbar("Pipeline job enqueued successfully.", { variant: "info" });
      await startJobQueue();
      newId = pipelineId;
    } else {
      newId = await RunPipeline(sortedNodes, nodeData, pipelineName, edges, enqueueSnackbar);
    }
    if (newId) {
      handleResultId(newId);
      navigate(`/app/pipelines/${newId}`, { 
        state: { activeTab: "results" }
      });
    }
  };

  const handleResultId = (id) => {
    setResultId(id);
  };

  const onNodeClick = (event, node) => {
    setSelectedNode(node);
  };

  const renderNodeDialogContent = () => {
    if (!selectedNode) return null;
    const { type, id } = selectedNode;

    if (type === "DataSelector") {
      return <DataSelectorNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]}/>;
    } else if (type === "DataExploration") {
      return <DataExplorationNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} data={nodeData}/>;
    } else if (type === "Train") {
      return <TrainNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} data={nodeData} />;
    } return null;
  };

  const onNodeMouseEnter = (event, node) => {
    if (validationErrors[node.id]) setHoveredNode(node);
  };

  const onNodeMouseLeave = () => {
    setHoveredNode(null);
  };

  useEffect(() => {
    if (hoveredNode && !nodes.find((n) => n.id === hoveredNode.id)) {
      setHoveredNode(null);
    }
  }, [nodes]);

  return (
    <CustomLayout title="Pipelines Module" subtitle="Create and manage your pipelines.">
    
      <Box sx={{ position: "relative", display: "flex", justifyContent: "center", alignItems: "center", mb: 2 }}>
        <Button 
          onClick={() => navigate('/app/pipelines')}
          sx={{ position: "absolute", left: 0, fontSize: "1rem" }}
        >
          <ArrowBackIosIcon />
        </Button>

        <Box>
          <Button 
            onClick={() => setActiveTab("flow")} 
            variant={activeTab === "flow" ? "contained" : "text"} 
            sx={{ mr: 1, fontSize: "1.1rem" }}
          >
            Design
          </Button>
          <Button 
            onClick={() => setActiveTab("results")} 
            variant={activeTab === "results" ? "contained" : "text"} 
            sx={{ fontSize: "1.1rem" }}
          >
            Results
          </Button>
        </Box>
      </Box>

      {activeTab === "flow" ? (
      <>
      <Box display="flex" height="85vh">
        <Box sx={{ width: 250, p: 2, backgroundColor: "#212121", overflowY: "auto" }}>
          <Typography variant="h6" gutterBottom sx={{ color: "#fff" }}>
            Nodes
          </Typography>
          {["DataSelector", "DataExploration", "Train", "Prediction"].map((nodeType) => (
            <Box
              key={nodeType}
              onDragStart={(e) => onDragStart(e, nodeType)}
              draggable
              sx={{ mb: 1, p: 1, backgroundColor: "#333", color: "#fff", borderRadius: 1, textAlign: "center", cursor: "grab" }}
            >
              <Typography>{nodeType}</Typography>
            </Box>
          ))}
        </Box>

        <Box sx={{ flexGrow: 1, p: 2, backgroundColor: "#fff" }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <TextField
              label="Pipeline Name"
              variant="outlined"
              size="small"
              backgroundColor="primary"
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
              sx={{
                mr: 2,
                input: { color: 'black' },
                '& .MuiOutlinedInput-root fieldset': { borderColor: 'black' },
                '& label': { color: 'black' },
              }}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={() => handleRun()}
            >
              Run
            </Button>
          </Box>

          <Box sx={{ width: '100%', height: '73vh' }} ref={flowWrapperRef}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeDoubleClick={onNodeClick} 
            onNodeMouseEnter={onNodeMouseEnter}
            onNodeMouseLeave={onNodeMouseLeave}
            nodeTypes={nodeTypes}
            fitView
            style={{
              width: '100%', 
              height: '100%',
              borderRadius: 12,
              background: "#f5f5f5",
              border: "1px solid #ccc",
              boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
            }}
          >
            {hoveredNode && (
              <Tooltip
                open
                title={Array.isArray(validationErrors[hoveredNode.id])
                    ? validationErrors[hoveredNode.id].join('\n')
                    : String(validationErrors[hoveredNode.id]).replace(/\. /g, '.\n')
                }
                placement="top"
                componentsProps={{
                  tooltip: {
                    sx: {
                      fontSize: '15px',
                      whiteSpace: 'pre-line',
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
    </CustomLayout>
  );
}

export default NewPipeline;
