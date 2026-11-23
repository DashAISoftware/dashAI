import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import SchemaIcon from "@mui/icons-material/Schema";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import PropTypes from "prop-types";
import { resolveLocalizedText } from "../../../utils/localize";

const INDENT = 40;

/**
 * Renders one node of the component tree: its icon, name, caption, the
 * add/remove controls, and recursively its children.
 *
 * @param {object} props
 * @param {object} props.node - The tree node to render.
 * @param {number} props.depth - Current depth, used for indentation.
 * @param {boolean} props.isRoot - Whether this is the root node.
 * @param {string|null} props.parentId - The parent node id (null for the root).
 * @param {function(string): (object|null)} props.findComponent - Component lookup.
 * @param {function(object): boolean} props.isContainer - Whether a node holds children.
 * @param {function(object): boolean} props.canAddChild - Whether a node accepts one more child.
 * @param {function(object): (string|null)} props.renderCaption - Caption of a node.
 * @param {function(string): void} props.onEdit - Opens the configuration of a node.
 * @param {function(string): void} props.onAddChild - Adds a child under a node.
 * @param {function(string, string): void} props.onRemoveChild - Removes a child.
 * @param {object} props.labels - Resolved texts (`configureNode`, `addChild`, `removeNode`).
 * @param {object} props.i18n - i18next instance used to localise component names.
 * @returns {JSX.Element|null} The node UI.
 */
export default function ComponentTreeNodeView({
  node,
  depth,
  isRoot,
  parentId,
  findComponent,
  isContainer,
  canAddChild,
  renderCaption,
  onEdit,
  onAddChild,
  onRemoveChild,
  labels,
  i18n,
}) {
  if (!node || !node.component) return null;

  const info = findComponent(node.component);
  const name =
    resolveLocalizedText(info?.display_name, i18n) ||
    node.component ||
    labels.configureNode;
  const container = isContainer(node);
  const cardX = depth * INDENT;
  const caption = renderCaption(node) || null;

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          ml: `${cardX}px`,
          position: "relative",
        }}
      >
        {depth > 0 && (
          <Box
            data-conn
            data-node={`${node.component}@${depth}`}
            sx={{
              position: "absolute",
              left: `${-INDENT / 2}px`,
              top: "50%",
              width: `${INDENT / 2}px`,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          />
        )}
        <Box
          data-card
          data-node={`${node.component}@${depth}`}
          role="button"
          tabIndex={0}
          aria-label={`${labels.configureNode}: ${name}`}
          onClick={() => onEdit(node.nodeId)}
          onKeyDown={(event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            onEdit(node.nodeId);
          }}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            px: 1.5,
            py: 1,
            border: "1px solid",
            borderColor: container
              ? "accent.purpleBorder"
              : "accent.amberBorder",
            borderRadius: 1,
            cursor: "pointer",
            backgroundColor: "background.paper",
            transition: "background-color 150ms ease-out",
            "&:focus-visible": {
              outline: "2px solid",
              outlineColor: "primary.main",
              outlineOffset: 2,
            },
            "@media (hover: hover)": {
              "&:hover": { backgroundColor: "action.hover" },
            },
          }}
        >
          {container ? (
            <AccountTreeIcon sx={{ fontSize: 18, color: "accent.purple" }} />
          ) : (
            <SchemaIcon sx={{ fontSize: 18, color: "accent.amber" }} />
          )}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
              maxWidth: 480,
            }}
          >
            <Typography variant="body2">{name}</Typography>
            {caption && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ maxWidth: "100%", overflowWrap: "anywhere" }}
              >
                {caption}
              </Typography>
            )}
          </Box>
        </Box>

        {container && canAddChild(node) && (
          <Tooltip title={labels.addChild}>
            <IconButton
              size="small"
              aria-label={labels.addChild}
              onClick={(event) => {
                event.stopPropagation();
                onAddChild(node.nodeId);
              }}
              sx={{ color: "primary.main" }}
            >
              <AddCircleOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}

        {!isRoot && (
          <Tooltip title={labels.removeNode}>
            <IconButton
              size="small"
              aria-label={labels.removeNode}
              onClick={(event) => {
                event.stopPropagation();
                onRemoveChild(parentId, node.nodeId);
              }}
              sx={{ color: "error.main" }}
            >
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
                data-spine
                data-node={`${node.component}@${depth}`}
                sx={{
                  position: "absolute",
                  left: `${cardX + INDENT / 2}px`,
                  top: 0,
                  bottom: 0,
                  width: "1px",
                  borderLeft: "1px solid",
                  borderColor: "divider",
                }}
              />
              <ComponentTreeNodeView
                node={child}
                depth={depth + 1}
                isRoot={false}
                parentId={node.nodeId}
                findComponent={findComponent}
                isContainer={isContainer}
                canAddChild={canAddChild}
                renderCaption={renderCaption}
                onEdit={onEdit}
                onAddChild={onAddChild}
                onRemoveChild={onRemoveChild}
                labels={labels}
                i18n={i18n}
              />
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

ComponentTreeNodeView.propTypes = {
  node: PropTypes.object.isRequired,
  depth: PropTypes.number.isRequired,
  isRoot: PropTypes.bool.isRequired,
  parentId: PropTypes.string,
  findComponent: PropTypes.func.isRequired,
  isContainer: PropTypes.func.isRequired,
  canAddChild: PropTypes.func.isRequired,
  renderCaption: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onAddChild: PropTypes.func.isRequired,
  onRemoveChild: PropTypes.func.isRequired,
  labels: PropTypes.object.isRequired,
  i18n: PropTypes.object.isRequired,
};
