import React, { useState, useCallback } from "react";
import { Box, Typography, Dialog, DialogTitle, DialogActions, Button } from "@mui/material";
import ReactFlow, { addEdge, Background, Controls, useEdgesState, useNodesState } from "reactflow";
import 'reactflow/dist/style.css';
import CustomLayout from "../../components/custom/CustomLayout";
import RunNode from "./nodes/Run";
import DataLoaderNode from "./nodes/DataLoaderNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TaskSelectorNode from "./nodes/TaskSelectorNode";
import MetricsNode from "./nodes/MetricsNode";

// const nodeTypes = {
//   DataLoader: DataLoaderNode,
//   DataExploration: DataExplorationNode,
//   TaskSelector: TaskSelectorNode,
//   Metrics: MetricsNode,
// };

function PipelinesPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [runNode, setRunNode] = useState(null);
  //const [nodeData, setNodeData] = useState({});
  const [nodeData, setNodeData] = useState({
    "DataLoader-0": { filePath: "data.csv" },
    "DataExploration-1": { analysisType: "summary" },
    "TaskSelector-2": { task: "classification" },
    "Metrics-3": { metric: "accuracy" },
  });

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
    };

    setNodes((nds) => nds.concat(newNode));
  }, [dragging, nodes.length, setNodes]);

  const onConnect = (params) => setEdges((eds) => addEdge(params, eds));

  const onNodeClick = (event, node) => {
    if (node.type === "Run") {
      setRunNode(node);
    } else {
      setSelectedNode(node);
    }
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

  const renderNodeDialogContent = () => {
    if (!selectedNode) return null;
    const { type, id } = selectedNode;

    if (type === "DataLoader") {
      return <DataLoaderNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)}/>;
    } else if (type === "DataExploration") {
      return <DataExplorationNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedConfig={nodeData[id]} />;
    } else if (type === "TaskSelector") {
      return <TaskSelectorNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedTask={nodeData[id]?.task || ""}/>;
    } else if (type === "Metrics") {
      return <MetricsNode open={!!selectedNode} onClose={handleCloseDialog} onSave={(data) => handleSaveNodeData(id, data)} savedMetrics={nodeData[id]?.metrics || []} />;
    }
    return null;
  };

  const renderRunNodeContent = () => {
    if (!runNode) return null;
    return <RunNode node={runNode} edges={edges} nodes={nodes} pipelineName="My Pipeline" onSaved={() => setRunNode(null)} nodeData={nodeData} />;
  };
  
  return (
    <CustomLayout title="Pipelines Module">
      <Box display="flex" height="100vh">
        <Box sx={{ width: 300, p: 2, backgroundColor: "#212121", overflowY: "auto" }}>
          <Typography variant="h6" gutterBottom sx={{ color: "#fff" }}>
            Nodes
          </Typography>
          {["DataLoader", "DataExploration", "TaskSelector", "Metrics", "Run"].map((nodeType) => (
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
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={(event) => event.preventDefault()}
            onNodeClick={onNodeClick} 
            // nodeTypes={nodeTypes}
            fitView
            style={{ width: '100%', height: '100%' }}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </Box>

        <Dialog open={!!selectedNode} onClose={handleCloseDialog}>
          <DialogTitle>{selectedNode?.data?.label || "Node Details"}</DialogTitle>
          {renderNodeDialogContent()}
          <DialogActions>
            <Button onClick={handleCloseDialog} color="primary">
              Close
            </Button>
          </DialogActions>
        </Dialog>
        {runNode && renderRunNodeContent()}
      </Box>
    </CustomLayout>
  );
}

export default PipelinesPage;
