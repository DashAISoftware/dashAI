import React, { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { Box, Typography, Dialog, TextField, Button, Tooltip } from "@mui/material";
import ArrowBackIosIcon from '@mui/icons-material/ArrowBackIos';
import ReactFlow, { addEdge, Background, Controls, useEdgesState, useNodesState, useReactFlow } from "reactflow";
import 'reactflow/dist/style.css';
import CustomLayout from "../../components/custom/CustomLayout";
import RunPipeline from "./nodes/Run";
import PipelineResults from "./Results";
import { getPipelineById } from "../../api/pipeline";
import { useParams, useNavigate } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { useSnackbar } from "notistack";
import { validatePipeline, sortNodes } from "./ValidatePipeline"
import { getNodeHelp, buildNodeHelp } from "./nodeHelp";
import { getNodeTypesMap, getNodeTypes } from "./nodeTypes";
import nodeComponentRegistry from "./nodeComponentRegistry";

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
  const [nodeHelp, setNodeHelp] = useState({});
  const [availableNodes, setAvailableNodes] = useState([]);
  const [nodeTypesMap, setNodeTypesMap] = useState([]);
  const [nodeIdCounter, setNodeIdCounter] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      const nodes = await getNodeTypes();
      setAvailableNodes(nodes);
      buildNodeHelp(nodes)
    };
    fetchData();
    async function loadNodeTypes() {
      const types = await getNodeTypesMap();
      setNodeTypesMap(types);
    }
    loadNodeTypes();
  }, []);

  const nodeTypes = useMemo(
    () => ({
      ...nodeTypesMap
    }),
    [nodeTypesMap],
  );

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

    const nodeId = `${dragging}-${nodeIdCounter}`;
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
    setNodeIdCounter((prev) => prev + 1);
  }, [dragging, nodes.length, setNodes, screenToFlowPosition, validationErrors, nodeIdCounter]);

  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        const nodeInfo = availableNodes.find((n) => n.type === node.type);
        const hasError = !!validationErrors[node.id];
        const needsConfig = nodeInfo?.requiresConfiguration ?? true;
        const isConfigured = nodeData[node.id] !== undefined;

        return {
          ...node,
          data: {
            ...node.data,
            hasError,
            notConfigured: needsConfig && !isConfigured,
            errors: validationErrors[node.id],
            icon: nodeInfo?.icon || null,
            name: nodeInfo?.name || node.type,
            source: nodeInfo?.source || false,
            target: nodeInfo?.target || false,
            type: nodeInfo?.type || node.type,
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
          position: { x: idx * 160, y: 100 + (idx % 2) * 100 },
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

  useEffect(() => {
    const validate = async () => {
      const errors = await validatePipeline(nodes, edges);
      setValidationErrors(errors);
    };
    validate();
  }, [nodes.length, edges]);

  const handleRun = async () => {
    const sortedNodes = sortNodes(nodes, edges);
    const errors = await validatePipeline(sortedNodes, edges);
    if (Object.keys(errors).length > 0) {
      enqueueSnackbar("Error in pipeline", { variant: "error" });
      return;
    }
    const newId = await RunPipeline(sortedNodes, nodeData, pipelineName, edges, enqueueSnackbar, pipelineId);
    if (newId) {
      handleResultId(newId);
      setActiveTab("results");
      navigate(`/app/pipelines/${newId}`);
    }
  };

  const handleResultId = (id) => {
    setResultId(id);
  };

  const onNodeClick = (event, node) => {
    setSelectedNode(node);
  };

  const onNodeHelp = (event, node) => {
    setNodeHelp(node);
  };

  function getConnectedNodeData(selectedNode) {
    const visited = new Set();
    const result = [];

    function traverseBackwards(nodeId) {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      const node = nodes.find(n => n.id === nodeId);
      if (node && nodeData[nodeId]) {
        result.push(nodeData[nodeId]);
      }
      const incomingEdges = edges.filter(edge => edge.target === nodeId);
      for (const edge of incomingEdges) {
        traverseBackwards(edge.source);
      }
    }

    traverseBackwards(selectedNode.id);
    return result;
  }

  const renderNodeDialogContent = () => {
    if (!selectedNode) return null;
    const { type, id } = selectedNode;
    const NodeComponent = nodeComponentRegistry[type];
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

  const onNodeMouseEnter = (event, node) => {
    if (validationErrors[node.id]) setHoveredNode(node);
  };

  const onNodeMouseLeave = () => {
    setHoveredNode(null);
  };

  useEffect(() => {
    if (
      hoveredNode && 
      (!nodes.find((n) => n.id === hoveredNode.id) || !validationErrors[hoveredNode.id])
    ) {
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
          {availableNodes.map((node) => (
            <Box
              key={node.type}
              onDragStart={(e) => onDragStart(e, node.type)}
              draggable
              sx={{ mb: 1, p: 1, backgroundColor: "#333", color: "#fff", borderRadius: 1, textAlign: "center", cursor: "grab" }}
            >
              <Typography>{node.name || node.type}</Typography>
            </Box>
          ))}

          <Box sx={{ p: 2, borderTop: '1px solid #ccc', backgroundColor: "#212121", mt: 2 }}>
              {(() => {
                const help = getNodeHelp(nodeHelp?.type || "Pipeline");
                return (
                  <>
                    <Typography variant="h6" sx={{ color: "#fff" }}>
                      {help.name || nodeHelp?.type || "Pipeline"} Help
                    </Typography>
                    <Typography variant="body1" sx={{ mb: 1, color: "#ddd" }}>
                      {help.description}
                    </Typography>
                    {help.input && (
                      <Typography variant="body2" sx={{ color: "#ccc" }}>
                        <u>Inputs:</u> {help.input || "None"}
                      </Typography>
                    )}
                    {help.output && (
                      <Typography variant="body2" sx={{ color: "#ccc" }}>
                        <u>Outputs:</u> {help.output || "None"}
                      </Typography>
                    )}
                    {help.next && (
                      <Typography variant="body2" sx={{ color: "#ccc" }}>
                        <u>Can be followed by:</u> {help.next || "None"}
                      </Typography>
                    )}
                  </>
                );
              })()}
            </Box>
          </Box>

        <Box sx={{ flexGrow: 1, p: 2, backgroundColor: "#fff" }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <TextField
              label="Pipeline Name"
              variant="outlined"
              size="small"
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
            onNodeClick={onNodeHelp}
            onPaneClick={() => setNodeHelp(null)}
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
