import { useState, useEffect, useMemo } from "react";
import { useEdgesState, useNodesState } from "reactflow";
import { useSnackbar } from "notistack";
import {
  validatePipeline,
  sortNodes,
  getNodeTypes,
  getNodeTypesMap,
  buildNodeHelp,
} from "../components/pipelines";
import { getPipelineById, getPipelines } from "../api/pipeline";
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

  // Name validation states
  const [nameError, setNameError] = useState(false);
  const [nameErrorMessage, setNameErrorMessage] = useState("");
  const [userHasModifiedName, setUserHasModifiedName] = useState(false);
  const [existingPipelines, setExistingPipelines] = useState([]);
  const [nodeIdCounter, setNodeIdCounter] = useState(0);
  const { enqueueSnackbar } = useSnackbar();

  // Generate default name for new pipelines
  const { defaultName } = useMemo(() => {
    if (pipelineId) return { defaultName: null };

    const result = generateSequentialName({
      base: "Pipeline",
      items: existingPipelines,
    });

    return result;
  }, [existingPipelines, pipelineId]);

  // Load existing pipelines for name generation
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

  // Load node types and available nodes
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

  // Set initial name validation and default value for new pipelines
  useEffect(() => {
    if (defaultName && !userHasModifiedName && !pipelineId) {
      if (
        pipelineName === "undefined" ||
        pipelineName.startsWith("Pipeline_")
      ) {
        setPipelineName(defaultName);
        setNameError(false);
        setNameErrorMessage("");
      }
    } else if (pipelineName === "" && userHasModifiedName) {
      setNameError(true);
      setNameErrorMessage("Name is required");
    }
  }, [defaultName, pipelineName, userHasModifiedName, pipelineId]);

  // Handle active tab changes
  useEffect(() => {
    if (location.state?.activeTab) {
      setActiveTab(location.state.activeTab);
    }
  }, [location.state?.activeTab]);

  // Load existing pipeline
  useEffect(() => {
    if (pipelineId) {
      (async () => {
        const pipeline = await getPipelineById(pipelineId);

        // Get node types to assign source/target properties
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

        // Update nodeIdCounter
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

  // Reset editor when switching to new pipeline route
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
      setPipelineName("undefined");
      setActiveTab("flow");
    }
  }, [pipelineId]);

  // Validate pipeline
  useEffect(() => {
    const validate = async () => {
      const errors = await validatePipeline(nodes, edges);
      setValidationErrors(errors);
    };
    validate();
  }, [nodes.length, edges]);

  // Update node data with validation info
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

  // Event handlers
  const onDragStart = (event, nodeType) => {
    setDragging(nodeType);
    event.dataTransfer.setData("text/plain", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  // Handle pipeline name input changes with validation
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
    // Check if name is valid
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

  // Clean up hovered node when nodes change
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
    handlePipelineNameChange,
  };
}
