import React, { useState, useCallback, useEffect } from "react";
import { Box, Typography, Dialog, DialogTitle, DialogActions, Button } from "@mui/material";
import ReactFlow, { addEdge, Background, Controls, useEdgesState, useNodesState } from "reactflow";
import 'reactflow/dist/style.css';
import CustomLayout from "../../components/custom/CustomLayout";
import RunPipeline from "./nodes/Run";
import DataLoaderNode from "./nodes/DataLoaderNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TaskModelNode from "./nodes/TaskSelectorNode";
import TrainNode from "./nodes/TrainNode";
import MetricsNode from "./nodes/MetricsNode";
import SplitDataNode from "./nodes/SplitDataNode";
import PredictionNode from "./nodes/PredictionNode";
import PipelineResults from "./Results";

const nodeTypes = {
  DataSeldector: DataLoaderNode,
  DataExploration: DataExplorationNode,
  SplitData: SplitDataNode,
  TaskModel: TaskModelNode,
  Train: TrainNode,
  Evaluate: MetricsNode,
  Prediction: PredictionNode,
};

function PipelinesPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [nodeData, setNodeData] = useState({});
  const [activeTab, setActiveTab] = useState("flow");
  const [resultId, setResultId] = useState(null);

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
  };

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

  const handleRun = async () => {
    const pipelineId = await RunPipeline(nodes, nodeData);
    console.log("Pipeline IDdd:", pipelineId);
    if (pipelineId) {
      handleResultId(pipelineId);
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

    if (type === "DataLoader") {
      return <DataLoaderNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]}/>;
    } else if (type === "DataExploration") {
      return <DataExplorationNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} data={nodeData}/>;
    } else if (type === "Train") {
      return <TrainNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} data={nodeData} />;
    } else if (type === "Prediction") {
      return <PredictionNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} />;
    } return null;
  };

  return (
    <CustomLayout title="Pipelines Module" subtitle="Create and manage your pipelines.">
      <Box sx={{ borderBottom: 1, borderColor: 'divider', display: "flex", justifyContent: "center", px: 2, pb: 1 }}>
        <Button onClick={() => setActiveTab("flow")} variant={activeTab === "flow" ? "contained" : "text"} sx={{ mr: 1, fontSize: "1.1rem"}}>
          Design
        </Button>
        <Button onClick={() => setActiveTab("results")} variant={activeTab === "results" ? "contained" : "text"} sx={{ fontSize: "1.1rem"}}>
          Results
        </Button>
      </Box>

      {activeTab === "flow" ? (
      <>
      <Box display="flex" height="100vh">
        <Box sx={{ width: 300, p: 2, backgroundColor: "#212121", overflowY: "auto" }}>
          <Typography variant="h6" gutterBottom sx={{ color: "#fff" }}>
            Nodes
          </Typography>
          {["DataLoader", "DataExploration", "Train", "Prediction"].map((nodeType) => (
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
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
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
        <Dialog open={!!selectedNode} onClose={handleCloseDialog}>
           {renderNodeDialogContent()}
         </Dialog>
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

export default PipelinesPage;
