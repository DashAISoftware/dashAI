import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Alert, Box, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import useComponentRegistry from "../../../hooks/useComponentRegistry";
import { resolveDefaults as resolveSchemaDefaults } from "../../../utils/schema";
import { resolveLocalizedText } from "../../../utils/localize";
import { EMPTY_COMPONENT_NAME } from "../../../constants/rag";
import FormSchema from "../FormSchema";
import ComponentTreeNodeView from "./ComponentTreeNodeView";
import ComponentTreeNodeConfig from "./ComponentTreeNodeConfig";
import {
  buildNodeFromRef,
  collectUnknownNames,
  createIdFactory,
  findChildrenField,
  findNode,
  findParentNode,
  getChildRefs,
  selectableOptions,
  serializeNode,
  updateAt,
} from "./componentTreeUtils";

/**
 * Generic interactive tree for components that contain other components.
 *
 * Nothing in it names a component class. A node is a container when its schema
 * declares a list of components, the children field and the parent class the
 * children must inherit come from that declaration, and the root's options come
 * from the `parent` prop. So any registry parent and any component with such a
 * field work, and new components appear without changes here.
 *
 * Domain behaviour is injected: the form that edits a node's params, how to
 * resolve its defaults, its caption, its texts, and an optional side panel.
 *
 * @param {object} props
 * @param {string} props.rootComponent - Name of the root (container) component.
 * @param {object} [props.rootParams] - Initial params of the root, including
 *   its children under the children field.
 * @param {function({component: string, params: object}): void} props.onChange -
 *   Receives the serialised tree on every change, and `{findComponent}` as a
 *   second argument so the caller can inspect component schemas.
 * @param {function({component: string, params: object}, {findComponent:
 *   function}): void} [props.onLoad] - Receives the initial tree once it is
 *   built, so a caller can validate it before the first edit. It is not an
 *   edit: `onChange` is never called for it, so nothing is written back.
 * @param {string} props.parent - Registry parent class whose components the
 *   root may be.
 * @param {function(string): Promise<object>} [props.resolveDefaults] - Default
 *   form values of a component. Defaults to the schema defaults.
 * @param {React.ElementType} [props.FormComponent] - Schema form that edits a
 *   node's params. Defaults to the generic `FormSchema`.
 * @param {function({node: object, info: object, findComponent: function,
 *   t: function, i18n: object}): (string|null)} [props.renderCaption] - Caption
 *   of a node. Defaults to the component's description.
 * @param {object} [props.labels] - Texts overriding the generic ones
 *   (`loading`, `configureNode`, `addChild`, `removeNode`, `selectComponent`,
 *   `parameters`, `containerNote`).
 * @param {React.ReactNode} [props.sideContent] - Content shown left of the tree.
 * @returns {JSX.Element} The tree builder.
 */
export default function ComponentTreeBuilder({
  rootComponent,
  rootParams,
  onChange,
  parent,
  resolveDefaults = resolveSchemaDefaults,
  FormComponent = FormSchema,
  renderCaption,
  labels: labelOverrides,
  sideContent = null,
  onLoad,
}) {
  const { t, i18n } = useTranslation(["common"]);
  const { registry, error: registryError } = useComponentRegistry(parent);
  const [tree, setTree] = useState(null);
  const [rootUnknown, setRootUnknown] = useState(false);
  const [editing, setEditing] = useState(null);
  const [editingParentId, setEditingParentId] = useState(null);
  const nextIdRef = useRef(createIdFactory());
  const rootParamsRef = useRef(rootParams);
  const onLoadRef = useRef(onLoad);

  const labels = useMemo(
    () => ({
      loading: t("common:loading"),
      configureNode: t("common:componentTree.configureNode"),
      addChild: t("common:componentTree.addChild"),
      removeNode: t("common:componentTree.removeNode"),
      selectComponent: t("common:componentTree.selectComponent"),
      parameters: t("common:componentTree.parameters"),
      containerNote: t("common:componentTree.containerNote"),
      ...labelOverrides,
    }),
    [t, labelOverrides],
  );

  const findComponent = useCallback(
    (name) => registry?.byName.get(name) ?? null,
    [registry],
  );
  const getChildrenField = useCallback(
    (name) => findChildrenField(findComponent(name)?.schema),
    [findComponent],
  );
  const isContainer = useCallback(
    (node) => Boolean(getChildrenField(node.component)),
    [getChildrenField],
  );
  const canAddChild = useCallback(
    (node) => {
      const field = getChildrenField(node.component);
      if (!field) return false;
      if (field.maxItems == null) return true;
      return node.children.filter((c) => c.component).length < field.maxItems;
    },
    [getChildrenField],
  );

  /**
   * Serialises the tree and reports it through `onChange`.
   * @param {object} root - The current tree root.
   */
  const emit = useCallback(
    (root) => onChange(serializeNode(root, findComponent), { findComponent }),
    [onChange, findComponent],
  );

  useEffect(() => {
    rootParamsRef.current = rootParams;
    onLoadRef.current = onLoad;
  });

  useEffect(() => {
    if (!registry) return;
    nextIdRef.current = createIdFactory();
    const root = buildNodeFromRef(
      { component: rootComponent, params: rootParamsRef.current ?? {} },
      findComponent,
      nextIdRef.current,
    );
    setRootUnknown(root.unknown === true);
    setTree(root.unknown ? null : root);
    if (!root.unknown) {
      onLoadRef.current?.(serializeNode(root, findComponent), {
        findComponent,
      });
    }
  }, [registry, rootComponent, findComponent]);

  /**
   * Replaces the tree and reports it to the owner.
   * @param {object} updated - The new tree root.
   */
  const commitTree = (updated) => {
    setTree(updated);
    emit(updated);
  };

  /**
   * Persists a node's component and params into the tree. When the component
   * becomes a container and the node has no children yet, the children its
   * default params declare are materialised so schema defaults are not
   * discarded. Keeping the same component preserves its children exactly
   * (including an empty list), so deliberately removed children are not
   * reseeded.
   * @param {string} nodeId - The target node id.
   * @param {string} component - The selected component name.
   * @param {object} params - The component params.
   */
  const handleSaveNode = (nodeId, component, params) => {
    const field = getChildrenField(component);
    const updated = updateAt(tree, nodeId, (node) => {
      const hasNoChildren = !node.children || node.children.length === 0;
      const seedDefaults =
        field && node.component !== component && hasNoChildren;
      let children = field ? node.children : [];
      if (seedDefaults) {
        children = getChildRefs({ params }, field.key).map((child) =>
          buildNodeFromRef(child, findComponent, nextIdRef.current),
        );
      }
      return { ...node, component, params: { ...params }, children };
    });
    commitTree(updated);
    setEditing(null);
    setEditingParentId(null);
  };

  /**
   * Adds an empty child under a parent and opens its configuration. Children
   * that were added but never configured are dropped.
   * @param {string} parentId - The parent node id.
   */
  const handleAddChild = (parentId) => {
    const id = nextIdRef.current();
    const updated = updateAt(tree, parentId, (node) => ({
      ...node,
      children: [
        ...node.children.filter((c) => c.component !== EMPTY_COMPONENT_NAME),
        {
          nodeId: id,
          component: EMPTY_COMPONENT_NAME,
          params: {},
          children: [],
        },
      ],
    }));
    commitTree(updated);
    setEditingParentId(parentId);
    setEditing(id);
  };

  /**
   * Removes a child from its parent.
   * @param {string} parentId - The parent node id.
   * @param {string} childId - The child node id.
   */
  const handleRemoveChild = (parentId, childId) => {
    const updated = updateAt(tree, parentId, (node) => ({
      ...node,
      children: node.children.filter((c) => c.nodeId !== childId),
    }));
    commitTree(updated);
  };

  const editingNode = tree && editing ? findNode(tree, editing) : null;
  const options = useMemo(() => {
    if (!tree || !editing || !registry) return [];
    const container = findParentNode(tree, editing);
    let optionsParent = parent;
    if (container) {
      optionsParent = getChildrenField(container.component)?.parent;
    }
    return selectableOptions(
      registry.optionsByParent[optionsParent],
      t("common:other"),
    );
  }, [tree, editing, registry, parent, getChildrenField, t]);

  const captionOf = useCallback(
    (node) => {
      if (node.unknown) return null;
      const info = findComponent(node.component);
      if (renderCaption) {
        return renderCaption({
          node,
          info,
          findComponent,
          t,
          i18n,
        });
      }
      return resolveLocalizedText(info?.description, i18n);
    },
    [findComponent, renderCaption, t, i18n],
  );

  if (registryError) {
    return (
      <Alert severity="error" sx={{ py: 0.5 }}>
        {t("common:componentTree.loadFailed", { reason: registryError })}
      </Alert>
    );
  }

  if (rootUnknown) {
    return (
      <Alert severity="error" sx={{ py: 0.5 }}>
        {t("common:componentTree.unknownComponent", {
          component: rootComponent,
        })}
      </Alert>
    );
  }

  if (!tree) {
    return (
      <Box sx={{ py: 4, textAlign: "center" }}>
        <Typography variant="body2" color="text.secondary">
          {labels.loading}
        </Typography>
      </Box>
    );
  }

  const unknownNames = [...new Set(collectUnknownNames(tree))];

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        gap: 2,
        alignItems: "flex-start",
      }}
    >
      {sideContent}

      <Box sx={{ flex: 1, minWidth: 0 }}>
        {unknownNames.map((component) => (
          <Alert key={component} severity="error" sx={{ py: 0.5, mb: 1 }}>
            {t("common:componentTree.unknownChild", { component })}
          </Alert>
        ))}
        <ComponentTreeNodeView
          node={tree}
          depth={0}
          isRoot
          parentId={null}
          findComponent={findComponent}
          isContainer={isContainer}
          canAddChild={canAddChild}
          renderCaption={captionOf}
          onEdit={(id) => setEditing(id)}
          onAddChild={handleAddChild}
          onRemoveChild={handleRemoveChild}
          labels={labels}
          i18n={i18n}
        />
      </Box>

      {editing && (
        <ComponentTreeNodeConfig
          open
          nodeId={editing}
          nodeData={editingNode}
          options={options}
          getChildrenField={getChildrenField}
          resolveDefaults={resolveDefaults}
          FormComponent={FormComponent}
          labels={labels}
          onSave={handleSaveNode}
          onClose={() => {
            if (
              editingNode &&
              editingNode.component === EMPTY_COMPONENT_NAME &&
              editingParentId
            ) {
              handleRemoveChild(editingParentId, editing);
            }
            setEditing(null);
            setEditingParentId(null);
          }}
        />
      )}
    </Box>
  );
}

ComponentTreeBuilder.propTypes = {
  rootComponent: PropTypes.string.isRequired,
  rootParams: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  parent: PropTypes.string.isRequired,
  resolveDefaults: PropTypes.func,
  FormComponent: PropTypes.elementType,
  renderCaption: PropTypes.func,
  labels: PropTypes.object,
  sideContent: PropTypes.node,
  onLoad: PropTypes.func,
};
