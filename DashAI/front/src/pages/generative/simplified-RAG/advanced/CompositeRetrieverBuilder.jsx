import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import PsychologyIcon from "@mui/icons-material/Psychology";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRetrieverComponents, getRetrievalParadigm } from "../../../../api/rag";
import RetrieverNodeConfig from "./RetrieverNodeConfig";

const COMPOSITE_TYPES = ["SequentialRetriever", "ParallelRetriever", "MMRRerankerRetriever"];
let _nodeIdCounter = 0;
function nextId() {
  return `n_${++_nodeIdCounter}`;
}

export default function CompositeRetrieverBuilder({
  rootComponent,
  rootParams,
  onChange,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);
  const [allComponents, setAllComponents] = useState([]);
  const [leafRegistry, setLeafRegistry] = useState({});
  const [editing, setEditing] = useState(null);
  const [tree, setTree] = useState(null);

  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      const paradigms = await getRetrievalParadigm();
      const leaves = paradigms.filter((p) => !COMPOSITE_TYPES.includes(p.name));
      const leafMap = {};
      for (const leaf of leaves) {
        const children = await getRetrieverComponents(leaf.name);
        leafMap[leaf.name] = (children || []).filter((c) => c.configurable_object !== false);
      }
      setAllComponents(paradigms);
      setLeafRegistry(leafMap);
      setReady(true);
    })();
  }, []);

  useEffect(() => {
    if (!ready) return;

    _nodeIdCounter = 0;
    const fromParams = rootParams?.children || [];

    const buildFromParams = (child) => {
      const id = nextId();
      const comp = findComponent(child.component);
      const node = { nodeId: id, component: child.component, params: child.params || {}, children: [] };
      if (COMPOSITE_TYPES.includes(child.component) && child.children?.length) {
        node.children = child.children.map(buildFromParams).filter(Boolean);
      }
      return comp ? node : null;
    };

    const existingChildren = fromParams.map(buildFromParams).filter(Boolean);

    setTree({
      nodeId: nextId(),
      component: rootComponent,
      params: rootParams || {},
      children: existingChildren,
    });
  }, [ready, rootComponent]);

  const findComponent = (name) => {
    const direct = allComponents.find((c) => c.name === name);
    if (direct) return direct;
    for (const key of Object.keys(leafRegistry)) {
      const found = (leafRegistry[key] || []).find((c) => c.name === name);
      if (found) return found;
    }
    return null;
  };

  const emit = useCallback(
    (t) => {
      const ser = (n) => {
        const s = { component: n.component, params: n.params || {} };
        if (COMPOSITE_TYPES.includes(n.component) && n.children.length > 0) {
          s.children = n.children.map(ser);
        }
        return s;
      };
      onChange({
        component: t.component,
        params: { ...t.params, children: t.children.map(ser) },
      });
    },
    [onChange],
  );

  const updateAt = (root, nodeId, fn) => {
    const walk = (n) => {
      if (n.nodeId === nodeId) return fn(n);
      if (n.children) return { ...n, children: n.children.map(walk) };
      return n;
    };
    return walk(root);
  };

  const handleSaveNode = (nodeId, component, params) => {
    const isComposite = COMPOSITE_TYPES.includes(component);
    setTree((prev) => {
      const updated = updateAt(prev, nodeId, (n) => ({
        ...n,
        component,
        params: { ...params },
        children: isComposite ? n.children : [],
      }));
      emit(updated);
      return updated;
    });
    setEditing(null);
  };

  const handleAddChild = (parentId) => {
    const id = nextId();
    setTree((prev) => {
      const updated = updateAt(prev, parentId, (n) => ({
        ...n,
        children: [...n.children, { nodeId: id, component: "", params: {}, children: [] }],
      }));
      return updated;
    });
    setEditing(id);
  };

  const handleRemoveChild = (parentId, childId) => {
    setTree((prev) => {
      const updated = updateAt(prev, parentId, (n) => ({
        ...n,
        children: n.children.filter((c) => c.nodeId !== childId),
      }));
      emit(updated);
      return updated;
    });
  };

  if (!tree) {
    return (
      <Box sx={{ py: 4, textAlign: "center" }}>
        <Typography variant="body2" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "row", gap: 2, alignItems: "flex-start" }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0.5,
          mt: 1,
          minWidth: 90,
          flexShrink: 0,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            fontWeight: 600,
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          {t("generative:simplifiedRag.composite.allChunks")}
        </Typography>

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            my: 1,
          }}
        >
          <Box
            sx={{
              width: 0,
              height: 0,
              borderLeft: "14px solid transparent",
              borderRight: "14px solid transparent",
              borderTop: `20px solid ${theme.palette.divider}`,
            }}
          />
          <Box sx={{ width: 2, height: 24, bgcolor: "divider" }} />
          <Box
            sx={{
              width: 0,
              height: 0,
              borderLeft: "14px solid transparent",
              borderRight: "14px solid transparent",
              borderTop: `20px solid ${theme.palette.divider}`,
            }}
          />
          <Box sx={{ width: 2, height: 24, bgcolor: "divider" }} />
          <Box
            sx={{
              width: 0,
              height: 0,
              borderLeft: "14px solid transparent",
              borderRight: "14px solid transparent",
              borderTop: `20px solid ${theme.palette.divider}`,
            }}
          />
        </Box>

        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            fontWeight: 600,
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          {t("generative:simplifiedRag.composite.selectedChunks")}
        </Typography>
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <TreeNodeView
          node={tree}
          depth={0}
          isRoot
          parentId={null}
          findComponent={findComponent}
          onEdit={(id) => setEditing(id)}
          onAddChild={handleAddChild}
          onRemoveChild={handleRemoveChild}
          theme={theme}
          t={t}
        />
      </Box>

      {editing && (
        <RetrieverNodeConfig
          open
          nodeId={editing}
          nodeData={findNodeData(tree, editing)}
          allComponents={allComponents}
          leafRegistry={leafRegistry}
          onSave={handleSaveNode}
          onClose={() => setEditing(null)}
        />
      )}
    </Box>
  );
}

CompositeRetrieverBuilder.propTypes = {
  rootComponent: PropTypes.string.isRequired,
  rootParams: PropTypes.object,
  onChange: PropTypes.func.isRequired,
};


function findNodeData(tree, nodeId) {
  if (tree.nodeId === nodeId) return tree;
  if (tree.children) {
    for (const c of tree.children) {
      const found = findNodeData(c, nodeId);
      if (found) return found;
    }
  }
  return null;
}


function TreeNodeView({
  node,
  depth,
  isRoot,
  parentId,
  findComponent,
  onEdit,
  onAddChild,
  onRemoveChild,
  theme,
  t,
  children,
}) {
  if (!node || !node.component) return null;

  const info = findComponent(node.component);
  const getString = (val) => {
    if (!val) return null;
    if (typeof val === "string") return val;
    if (val.en) return val.en;
    return String(val);
  };
  const name = getString(info?.display_name) || getString(info?.name) || node.component || t("generative:simplifiedRag.composite.configureNode");
  const isComposite = COMPOSITE_TYPES.includes(node.component);
  const Indent = depth * 3;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: Indent, position: "relative" }}>
        {depth > 0 && (
          <Box
            sx={{
              position: "absolute",
              left: -Indent + (depth - 1) * 3 + 20,
              top: "50%",
              width: Indent - (depth - 1) * 3 - 20,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          />
        )}

        <Box
          onClick={() => onEdit(node.nodeId)}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            px: 1.5,
            py: 1,
            border: "1px solid",
            borderColor: isComposite ? "secondary.main" : "primary.main",
            borderRadius: 1,
            cursor: "pointer",
            backgroundColor: "background.paper",
            "&:hover": { backgroundColor: "action.hover" },
          }}
        >
          {isComposite ? (
            <AccountTreeIcon sx={{ fontSize: 18, color: "secondary.main" }} />
          ) : (
            <PsychologyIcon sx={{ fontSize: 18, color: "primary.main" }} />
          )}
          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem" }}>
            {name}
          </Typography>
        </Box>

        {isComposite && (
          <Tooltip title={t("generative:simplifiedRag.composite.addChild")}>
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); onAddChild(node.nodeId); }} sx={{ color: "primary.main" }}>
              <AddCircleOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}

        {!isRoot && (
          <Tooltip title={t("generative:simplifiedRag.composite.removeNode")}>
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); onRemoveChild(parentId, node.nodeId); }} sx={{ color: "error.main" }}>
              <RemoveCircleOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {node.children?.length > 0 && (
        <Box sx={{ position: "relative" }}>
          {node.children.filter(Boolean).map((child) => (
            <Box key={child.nodeId} sx={{ position: "relative" }}>
              <Box
                sx={{
                  position: "absolute",
                  left: Indent + 12,
                  top: 0,
                  bottom: 0,
                  width: 1,
                  borderLeft: "1px solid",
                  borderColor: "divider",
                }}
              />
              <TreeNodeView
                node={child}
                depth={depth + 1}
                isRoot={false}
                parentId={node.nodeId}
                findComponent={findComponent}
                onEdit={onEdit}
                onAddChild={onAddChild}
                onRemoveChild={onRemoveChild}
                theme={theme}
                t={t}
              />
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

TreeNodeView.propTypes = {
  node: PropTypes.object.isRequired,
  depth: PropTypes.number.isRequired,
  isRoot: PropTypes.bool.isRequired,
  parentId: PropTypes.string,
  findComponent: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onAddChild: PropTypes.func.isRequired,
  onRemoveChild: PropTypes.func.isRequired,
  theme: PropTypes.object.isRequired,
  t: PropTypes.func.isRequired,
};
