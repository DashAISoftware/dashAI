import { useState, useEffect, useMemo } from "react";
import { addEdge, useEdgesState, useNodesState } from "reactflow";
import { useSnackbar } from "notistack";
import {
  validatePipeline,
  sortNodes,
  getNodeTypes,
  getNodeTypesMap,
  buildNodeHelp,
} from "../components/pipelines";
import { getPipelineById, getPipelines, validateEdge } from "../api/pipeline";
import { generateSequentialName } from "../utils/nameGenerator";
import RunPipeline from "../components/pipelines/Run";

const TWO_OUTPUT_NODE_TYPES = new Set([
  "DataSelector",
  "SplitData",
  "TaskAndModel",
]);

const TWO_INPUT_NODE_TYPES = new Set(["MetricsEval"]);

const normalizeNodeHandles = (nodes = []) =>
  nodes.map((node) => {
    const shouldNormalizeSource = TWO_OUTPUT_NODE_TYPES.has(node.type);
    const shouldNormalizeTarget = TWO_INPUT_NODE_TYPES.has(node.type);

    if (!shouldNormalizeSource && !shouldNormalizeTarget) {
      return node;
    }

    return {
      ...node,
      ...(shouldNormalizeSource
        ? { sourceHandles: Math.max(2, Number(node.sourceHandles) || 0) }
        : {}),
      ...(shouldNormalizeTarget
        ? { targetHandles: Math.max(2, Number(node.targetHandles) || 0) }
        : {}),
    };
  });

export function usePipelineState(pipelineId, location, navigate) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [nodeData, setNodeData] = useState({});
  const [activeTab, setActiveTab] = useState(
    location.state?.activeTab || "flow",
  );
  const [resultId, setResultId] = useState(null);
  const [pipelineName, setPipelineName] = useState("undefined");
  const [validationErrors, setValidationErrors] = useState({});
  const [hoveredNode, setHoveredNode] = useState(null);
  const [nodeHelp, setNodeHelp] = useState({});
  const [availableNodes, setAvailableNodes] = useState([]);
  const [nodeTypesMap, setNodeTypesMap] = useState([]);
  const [nameError, setNameError] = useState(false);
  const [nameErrorMessage, setNameErrorMessage] = useState("");
  const [userHasModifiedName, setUserHasModifiedName] = useState(false);
  const [existingPipelines, setExistingPipelines] = useState([]);
  const [nodeIdCounter, setNodeIdCounter] = useState(0);
  const { enqueueSnackbar } = useSnackbar();

  const { defaultName } = useMemo(() => {
    if (pipelineId) return { defaultName: null };

    const result = generateSequentialName({
      base: "Pipeline",
      items: existingPipelines,
    });

    return result;
  }, [existingPipelines, pipelineId]);

  useEffect(() => {
    const fetchPipelines = async () => {
      try {
        const pipelines = await getPipelines();
        setExistingPipelines(pipelines);
      } catch (error) {
        console.error("Error fetching pipelines:", error);
      }
    };

    if (!pipelineId) {
      fetchPipelines();
    }
  }, [pipelineId]);

  useEffect(() => {
    const fetchData = async () => {
      const nodes = normalizeNodeHandles(await getNodeTypes());
      setAvailableNodes(nodes);
      buildNodeHelp(nodes);
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
      ...nodeTypesMap,
    }),
    [nodeTypesMap],
  );

  useEffect(() => {
    if (defaultName && !userHasModifiedName && !pipelineId) {
      setPipelineName(defaultName);
      setNameError(false);
      setNameErrorMessage("");
    } else if (pipelineName === "" && userHasModifiedName) {
      setNameError(true);
      setNameErrorMessage("Name is required");
    }
  }, [defaultName, pipelineName, userHasModifiedName, pipelineId]);

  useEffect(() => {
    if (location.state?.activeTab) {
      setActiveTab(location.state.activeTab);
    }
  }, [location.state?.activeTab]);

  useEffect(() => {
    if (pipelineId) {
      (async () => {
        const pipeline = await getPipelineById(pipelineId);
        const nodeTypes = normalizeNodeHandles(await getNodeTypes());

        const loadedNodes = pipeline.steps.map((step, idx) => {
          const nodeInfo = nodeTypes.find((n) => n.type === step.type);
          return {
            id: step.id,
            type: step.type,
            position: { x: idx * 160, y: 100 + (idx % 2) * 100 },
            data: {
              label: step.label,
              source: nodeInfo?.source || false,
              target: nodeInfo?.target || false,
              sourceHandles: nodeInfo?.sourceHandles || 1,
              targetHandles: nodeInfo?.targetHandles || 1,
              onDelete: () => {
                setNodes((nds) => nds.filter((n) => n.id !== step.id));
                setNodeData((prev) => {
                  const newData = { ...prev };
                  delete newData[step.id];
                  return newData;
                });
                setEdges((eds) =>
                  eds.filter(
                    (e) => e.source !== step.id && e.target !== step.id,
                  ),
                );
              },
            },
            sourcePosition: "right",
            targetPosition: "left",
          };
        });

        setNodes(loadedNodes);
        setEdges(pipeline.edges || []);
        const configMap = {};
        pipeline.steps.forEach((step) => {
          configMap[step.id] = step.config;
        });
        setNodeData(configMap);
        setResultId(pipelineId);
        setPipelineName(pipeline.name);
        setUserHasModifiedName(false);

        const maxCounter = Math.max(
          ...loadedNodes.map((node) => {
            const match = node.id.match(/-(\d+)$/);
            return match ? parseInt(match[1]) : -1;
          }),
          -1,
        );
        setNodeIdCounter(maxCounter + 1);
      })();
    }
  }, [pipelineId]);

  useEffect(() => {
    if (!pipelineId) {
      setNodes([]);
      setEdges([]);
      setNodeData({});
      setSelectedNode(null);
      setResultId(null);
      setValidationErrors({});
      setHoveredNode(null);
      setNodeHelp({});
      setNodeIdCounter(0);
      setUserHasModifiedName(false);
      setActiveTab("flow");
    }
  }, [pipelineId]);

  useEffect(() => {
    const validate = async () => {
      const errors = await validatePipeline(nodes, edges);
      setValidationErrors(errors);
    };
    validate();
  }, [nodes.length, edges]);

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
            sourceHandles: nodeInfo?.sourceHandles || 1,
            targetHandles: nodeInfo?.targetHandles || 1,
            type: nodeInfo?.type || node.type,
            configType: nodeInfo?.configType,
            configSchema: nodeInfo?.configSchema || null,
          },
        };
      }),
    );
  }, [validationErrors, nodeData, availableNodes]);

  const onDragStart = (event, nodeType) => {
    setDragging(nodeType);
    event.dataTransfer.setData("text/plain", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  const handlePipelineNameChange = (event) => {
    setPipelineName(event.target.value);
    setUserHasModifiedName(true);

    if (event.target.value.trim() === "") {
      setNameError(true);
      setNameErrorMessage("Name is required");
    } else {
      setNameError(false);
      setNameErrorMessage("");
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

  const handleRun = async () => {
    if (
      !pipelineName ||
      pipelineName.trim() === "" ||
      pipelineName === "undefined"
    ) {
      setNameError(true);
      setNameErrorMessage("Name is required");
      enqueueSnackbar("Pipeline name is required", { variant: "error" });
      return;
    }

    const unconfiguredNodes = nodes.filter((node) => node.data?.notConfigured);
    const sortedNodes = sortNodes(nodes, edges);
    const errors = await validatePipeline(sortedNodes, edges);
    if (Object.keys(errors).length > 0 || unconfiguredNodes.length > 0) {
      enqueueSnackbar("Error in pipeline", { variant: "error" });
      return;
    }
    const newId = await RunPipeline(
      sortedNodes,
      nodeData,
      pipelineName,
      edges,
      enqueueSnackbar,
      pipelineId,
    );
    if (newId) {
      setResultId(newId);
      setActiveTab("results");
      navigate(`/app/pipelines/${newId}`);
    }
  };

  const onNodeClick = (event, node) => {
    setSelectedNode(node);
  };

  const onNodeHelp = (event, node) => {
    setNodeHelp(node);
  };

  const onNodeMouseEnter = (event, node) => {
    if (validationErrors[node.id]) setHoveredNode(node);
  };

  const onNodeMouseLeave = () => {
    setHoveredNode(null);
  };

  const onPaneClick = () => {
    setNodeHelp(null);
  };

  const handleEdgeRemove = (event, edge) => {
    if (event?.stopPropagation) {
      event.stopPropagation();
    }
    setEdges((eds) =>
      eds.filter((e) => {
        if (edge?.id && e.id === edge.id) {
          return false;
        }
        return !(
          e.source === edge.source &&
          e.target === edge.target &&
          e.sourceHandle === edge.sourceHandle &&
          e.targetHandle === edge.targetHandle
        );
      }),
    );
  };

  const handleConnect = async (params) => {
    const sourceNode = nodes.find((node) => node.id === params.source);
    const targetNode = nodes.find((node) => node.id === params.target);

    if (!sourceNode || !targetNode) {
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
      return;
    }

    const currentOutputs = edges.filter(
      (edge) =>
        edge.source === params.source &&
        (params.sourceHandle
          ? edge.sourceHandle === params.sourceHandle
          : true),
    ).length;
    const currentInputs = edges.filter(
      (edge) =>
        edge.target === params.target &&
        (params.targetHandle
          ? edge.targetHandle === params.targetHandle
          : true),
    ).length;

    let validation = null;
    try {
      validation = await validateEdge({
        source: {
          nodeId: params.source,
          type: sourceNode.type,
          port: params.sourceHandle || null,
          currentConnections: currentOutputs,
        },
        target: {
          nodeId: params.target,
          type: targetNode.type,
          port: params.targetHandle || null,
          currentConnections: currentInputs,
        },
      });
    } catch (error) {
      console.error("Edge validation error:", error);
    }

    const shouldWarn = validation && validation.ok === false;
    const edgeColor = validation?.style?.edgeColor;
    const edgeClass = validation?.style?.edgeClass;

    if (shouldWarn && validation?.message) {
      enqueueSnackbar(validation.message, {
        variant: validation.severity === "warning" ? "warning" : "error",
      });
    }

    setEdges((eds) =>
      addEdge(
        {
          ...params,
          className: shouldWarn ? edgeClass : undefined,
          style:
            shouldWarn && edgeColor
              ? { stroke: edgeColor, strokeWidth: 2 }
              : undefined,
          markerEnd: {
            type: "arrowclosed",
            color: shouldWarn && edgeColor ? edgeColor : undefined,
          },
        },
        eds,
      ),
    );
  };

  useEffect(() => {
    if (
      hoveredNode &&
      (!nodes.find((n) => n.id === hoveredNode.id) ||
        !validationErrors[hoveredNode.id])
    ) {
      setHoveredNode(null);
    }
  }, [nodes, hoveredNode, validationErrors]);

  return {
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
    handleConnect,
    handleEdgeRemove,
    handlePipelineNameChange,
  };
}
