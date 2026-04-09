import { useState, useEffect, useRef } from "react";
import { Box, Typography, Collapse } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ItemBox from "./ItemBox";
import { t } from "i18next";

export default function GroupedCollapsibleList({
  groups = {}, // Object with group names as keys and items arrays as values
  selectedItemId,
  onItemClick,
  onItemDelete,
  onItemEdit,
  onItemInfo,
  title = t("common:items", "Items"),
  Icon,
  getItemDescription,
  getDeleteConfirmationContent,
  getDeleteConfirmationWarning,
  initialOpenGroups = {},
}) {
  const theme = useTheme();
  const [openGroups, setOpenGroups] = useState(initialOpenGroups);
  const selectedItemRef = useRef(null);

  // Auto-open group when an item is selected
  useEffect(() => {
    if (selectedItemId) {
      // Find which group contains the selected item
      for (const [groupName, items] of Object.entries(groups)) {
        if (items?.some((item) => item.id === selectedItemId)) {
          setOpenGroups((prev) => ({
            ...prev,
            [groupName]: true,
          }));
          break;
        }
      }
    }
  }, [selectedItemId, groups]);

  // Scroll to selected item after group is opened
  useEffect(() => {
    if (selectedItemId && selectedItemRef.current) {
      // Use setTimeout to ensure the Collapse animation has completed
      setTimeout(() => {
        selectedItemRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 350);
    }
  }, [selectedItemId, openGroups]);

  const toggleGroup = (groupName) => {
    setOpenGroups((prev) => ({
      ...prev,
      [groupName]: !prev[groupName],
    }));
  };

  const totalCount = Object.values(groups).reduce(
    (sum, items) => sum + (items?.length || 0),
    0,
  );

  const defaultGetDescription = (item) => item.description || "";

  return (
    <Box
      display="flex"
      flexDirection="column"
      pb={1}
      sx={{
        overflowY: "hidden",
        flex: 1,
        pl: 2,
        pr: 2,
        pt: 2,
      }}
    >
      {/* Main Header */}
      <Box
        display="flex"
        alignItems="center"
        py={0.5}
        px={1}
        mb={0.5}
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          borderRadius: 1,
          "&:hover": { bgcolor: theme.palette.ui.hover },
        }}
      >
        {Icon && (
          <Icon
            sx={{ color: theme.palette.primary.main, mr: 1, fontSize: 20 }}
          />
        )}
        <Typography
          sx={{
            ...theme.typography.cardTitle,
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
          {totalCount}
        </Box>
      </Box>

      {/* Groups - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          scrollbarGutter: "stable",
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
        {Object.entries(groups || {}).map(([groupName, items]) => (
          <Box key={groupName} mb={1}>
            {/* Group Header */}
            <Box
              display="flex"
              alignItems="center"
              sx={{
                cursor: "pointer",
                py: 0.5,
                px: 1,
                borderRadius: 1,
                "&:hover": {
                  bgcolor: theme.palette.ui.hover,
                },
              }}
              onClick={() => toggleGroup(groupName)}
            >
              {openGroups[groupName] ? (
                <KeyboardArrowDownIcon
                  sx={{ fontSize: 20, color: theme.palette.primary.main }}
                />
              ) : (
                <KeyboardArrowRightIcon
                  sx={{ fontSize: 20, color: theme.palette.primary.main }}
                />
              )}
              <Typography
                sx={{
                  ml: 1,
                  ...theme.typography.cardTitle,
                  textTransform: "capitalize",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  wordBreak: "break-all",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}
                color="text.primary"
              >
                {groupName}
              </Typography>
              <Box
                sx={{
                  ml: 1,
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
                {items?.length || 0}
              </Box>
            </Box>

            {/* Group Items */}
            <Collapse in={openGroups[groupName]} timeout="auto">
              <Box pl={2}>
                {items?.length ? (
                  items.map((item) => (
                    <ItemBox
                      key={item.id ?? item.name}
                      ref={item.id === selectedItemId ? selectedItemRef : null}
                      isSelected={item.id === selectedItemId}
                      name={item.name}
                      description={
                        getItemDescription
                          ? getItemDescription(item)
                          : defaultGetDescription(item)
                      }
                      id={item.id}
                      onClick={() => onItemClick(item.id)}
                      onDelete={() => onItemDelete(item.id)}
                      onEdit={(name) => onItemEdit(item.id, name)}
                      onInfo={
                        onItemInfo ? () => onItemInfo(item.id) : undefined
                      }
                      deleteConfirmationContent={
                        getDeleteConfirmationContent
                          ? getDeleteConfirmationContent(item)
                          : undefined
                      }
                      deleteConfirmationWarning={
                        getDeleteConfirmationWarning
                          ? getDeleteConfirmationWarning(item)
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
                      p: 2,
                    }}
                  >
                    {t("common:noItemsInGroup", "No items found.")}
                  </Typography>
                )}
              </Box>
            </Collapse>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
