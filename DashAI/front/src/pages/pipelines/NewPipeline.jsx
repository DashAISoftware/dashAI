import React, { useState, useCallback, useEffect } from "react";
import { Box, Typography, Dialog, TextField, Button  } from "@mui/material";
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowBackIosIcon from '@mui/icons-material/ArrowBackIos';import ReactFlow, { addEdge, Background, Controls, useEdgesState, useNodesState } from "reactflow";
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

const nodeTypes = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  Train: TrainNode,
  Prediction: PredictionNode,
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

  useEffect(() => {
    if (location.state?.activeTab) {
      setActiveTab(location.state.activeTab);
    }
  }, [location.state?.activeTab]);

  const onDragStart = (event, nodeType) => {
    setDragging(nodeType);
  };

  const onDrop = useCallback((event) => {
    event.preventDefault();
    const reactFlowBounds = event.target.getBoundingClientRect();
    const position = { x: event.clientX - reactFlowBounds.left, y: event.clientY - reactFlowBounds.top };
    
    const newNode = {
      id: `${dragging}-${nodes.length}`, 
      type: dragging, 
      position,
      data: { label: `${dragging} Node` },
      sourcePosition: "right",
      targetPosition: "left",
    };

    setNodes((nds) => nds.concat(newNode));
  }, [dragging, nodes.length, setNodes]);

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
    console.log("edges:", params);
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
  }, [pipelineId, setNodes, setEdges, setNodeData, setPipelineName, setResultId]);

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

  const handleRun = async () => {
    let newId;
    if (pipelineId) {
      await updatePipeline(pipelineId, { name: pipelineName, steps: buildSteps(nodes, nodeData), edges: edges });
      alert("Pipeline updated successfully!");
      newId = pipelineId;
    } else {
      newId = await RunPipeline(nodes, nodeData, pipelineName, edges);
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
      <Box display="flex" height="100vh">
        <Box sx={{ width: 300, p: 2, backgroundColor: "#212121", overflowY: "auto" }}>
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

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={(event) => event.preventDefault()}
            onNodeClick={onNodeClick} 
            //nodeTypes={nodeTypes}
            fitView
            style={{ width: '100%', height: '100%' }}
          >
            <Background />
            <Controls />
          </ReactFlow>
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
