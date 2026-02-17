import { useState } from "react";
import { Box, Typography, Collapse } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ItemBox from "./ItemBox";
import { t } from "i18next";

export default function CollapsibleList({
  items = [],
  selectedItemId,
  onItemClick,
  onItemDelete,
  onItemEdit,
  onItemInfo,
  defaultOpen = true,
  title = t("common:availableItems", "Available Items"),
  Icon = FolderIcon,
  getItemDescription,
}) {
  const theme = useTheme();
  const [open, setOpen] = useState(defaultOpen);
  const count = items?.length ?? 0;

  const defaultGetDescription = (item) => item.description || "";

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
          "&:hover": { bgcolor: theme.palette.ui.hover },
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon sx={{ fontSize: 20, color: theme.palette.primary.main, mr: 1 }} />

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
          color="text.primary"
        >
          {title}
        </Typography>

        <Box
          sx={{
            mr: 1,
            bgcolor: theme.palette.ui.scrollbar,
            color: theme.palette.text.primary,
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
          <KeyboardArrowDownIcon
            sx={{ fontSize: 20, color: theme.palette.primary.main }}
          />
        ) : (
          <KeyboardArrowRightIcon
            sx={{ fontSize: 20, color: theme.palette.primary.main }}
          />
        )}
      </Box>

      {/* Lista colapsable */}
      <Collapse
        in={open}
        timeout="auto"
        sx={{
          "&::-webkit-scrollbar": { width: "6px" },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: theme.palette.ui.scrollbar,
            borderRadius: "3px",
          },
          "&::-webkit-scrollbar-thumb:hover": {
            backgroundColor: theme.palette.ui.scrollbarHover,
          },
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
                description={
                  getItemDescription
                    ? getItemDescription(ds)
                    : defaultGetDescription(ds)
                }
                id={ds.id}
                onClick={() => onItemClick(ds.id)}
                onDelete={() => onItemDelete(ds.id)}
                onEdit={(name) => onItemEdit(ds.id, name)}
                onInfo={onItemInfo ? () => onItemInfo(ds.id) : undefined}
              />
            ))
          ) : (
            <Typography
              sx={{
                color: theme.palette.text.primary,
                opacity: 0.5,
                textAlign: "center",
                p: 2,
              }}
            >
              {t("common:noItemsAvailable", "No items available.")}
            </Typography>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
