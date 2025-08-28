import { useState } from "react";
import { Box, Typography, Collapse } from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ItemBox from "./ItemBox";

export default function CollapsibleList({
  items = [],
  selectedItemId,
  onItemClick,
  onItemDelete,
  onItemEdit,
  onItemInfo,
  defaultOpen = true,
  title = "Available Items",
  Icon = FolderIcon,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const count = items?.length ?? 0;

  return (
    <Box
      display="flex"
      flexDirection="column"
      // height="100%"
      // width="100%"
      pb={1}
      sx={{
        overflowY: "hidden",
        flex: 1,
        pl: 2,
        pr: 2,
        pt: 2,
      }}
    >
      {/* Header de la carpeta */}
      <Box
        display="flex"
        alignItems="center"
        sx={{
          cursor: "pointer",
          py: 0.5,
          px: 1,
          borderRadius: 1,
          "&:hover": { bgcolor: "rgba(255, 255, 255, 0.05)" },
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon sx={{ fontSize: 20, color: "#16FFFF", mr: 1 }} />

        <Typography
          sx={{
            fontSize: "0.95rem",
            fontWeight: 600,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flex: 1,
          }}
          title={title}
        >
          {title}
        </Typography>

        <Box
          sx={{
            mr: 1,
            bgcolor: "#374151",
            color: "white",
            borderRadius: "50%",
            width: 20,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
          }}
        >
          {count}
        </Box>

        {open ? (
          <KeyboardArrowDownIcon sx={{ fontSize: 20, color: "#16FFFF" }} />
        ) : (
          <KeyboardArrowRightIcon sx={{ fontSize: 20, color: "#16FFFF" }} />
        )}
      </Box>

      {/* Lista colapsable de datasets */}
      <Collapse
        in={open}
        timeout="auto"
        sx={{
          "&::-webkit-scrollbar": { width: "6px" },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "#374151",
            borderRadius: "3px",
          },
          "&::-webkit-scrollbar-thumb:hover": { backgroundColor: "#4B5563" },
          overflowY: "auto",
        }}
      >
        <Box pl={2}>
          {items?.length ? (
            items.map((ds) => (
              <ItemBox
                key={ds.id ?? ds.name}
                isSelected={ds.id === selectedItemId}
                name={ds.name}
                description={ds.description}
                id={ds.id}
                onClick={() => onItemClick(ds.id)}
                onDelete={() => onItemDelete(ds.id)}
                onEdit={(name) => onItemEdit(ds.id, name)}
                onInfo={onItemInfo ? () => onItemInfo(ds.id) : undefined}
              />
            ))
          ) : (
            <Typography
              sx={{ color: "#ffffff", opacity: 0.5, textAlign: "center", p: 2 }}
            >
              No items found
            </Typography>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
