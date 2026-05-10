import { useState, useEffect, useRef } from "react";
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
  getDeleteConfirmationContent,
  getDeleteConfirmationWarning,
}) {
  const theme = useTheme();
  const [open, setOpen] = useState(defaultOpen);
  const count = items?.length ?? 0;
  const prevCountRef = useRef(count);
  const lastItemRef = useRef(null);

  useEffect(() => {
    const prevCount = prevCountRef.current;

    if (count > prevCount && prevCount > 0) {
      setOpen(true);

      setTimeout(() => {
        if (lastItemRef.current) {
          lastItemRef.current.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        }
      }, 300);
    }

    prevCountRef.current = count;
  }, [count]);

  const defaultGetDescription = (item) => item.description || "";

  return (
    <Box
      display="flex"
      flexDirection="column"
      // height="100%"
      // width="100%"
      pb={4}
      sx={{
        overflowY: "hidden",
        flex: 1,
        pl: 4,
        pr: 4,
        pt: 4,
      }}
    >
      {/* Header de la carpeta */}
      <Box
        display="flex"
        alignItems="center"
        sx={{
          cursor: "pointer",
          py: 2,
          px: 4,
          borderRadius: 1,
          "&:hover": { bgcolor: theme.palette.ui.hover },
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon sx={{ fontSize: 20, color: theme.palette.primary.main, mr: 4 }} />

        <Typography
          variant="h5"
          sx={{
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

        <Typography
          variant="body2"
          component="div"
          sx={{
            mr: 4,
            bgcolor: theme.palette.ui.scrollbar,
            color: theme.palette.text.primary,
            borderRadius: "50%",
            width: 20,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {count}
        </Typography>

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

      {/* Collapsible list */}
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
        <Box pl={4}>
          {items?.length ? (
            items.map((ds, index) => (
              <ItemBox
                key={ds.id ?? ds.name}
                ref={index === items.length - 1 ? lastItemRef : null}
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
                deleteConfirmationContent={
                  getDeleteConfirmationContent
                    ? getDeleteConfirmationContent(ds)
                    : undefined
                }
                deleteConfirmationWarning={
                  getDeleteConfirmationWarning
                    ? getDeleteConfirmationWarning(ds)
                    : undefined
                }
              />
            ))
          ) : (
            <Typography
              sx={{
                color: theme.palette.text.primary,
                opacity: 0.5,
                textAlign: "center",
                p: 8,
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
