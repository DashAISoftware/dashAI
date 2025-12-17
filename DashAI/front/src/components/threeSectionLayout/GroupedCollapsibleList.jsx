import { useState } from "react";
import { Box, Typography, Collapse } from "@mui/material";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ItemBox from "./ItemBox";

export default function GroupedCollapsibleList({
  groups = {}, // Object with group names as keys and items arrays as values
  selectedItemId,
  onItemClick,
  onItemDelete,
  onItemEdit,
  onItemInfo,
  title = "Items",
  Icon,
  getItemDescription,
  initialOpenGroups = {},
}) {
  const [openGroups, setOpenGroups] = useState(initialOpenGroups);

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
          "&:hover": { bgcolor: "rgba(255, 255, 255, 0.05)" },
        }}
      >
        {Icon && <Icon sx={{ color: "#16FFFF", mr: 1, fontSize: 20 }} />}
        <Typography>{title}</Typography>
        <Box
          sx={{
            ml: 1,
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
          {totalCount}
        </Box>
      </Box>

      {/* Groups - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          "&::-webkit-scrollbar": { width: "6px" },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "#374151",
            borderRadius: "3px",
          },
          "&::-webkit-scrollbar-thumb:hover": { backgroundColor: "#4B5563" },
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
                  bgcolor: "rgba(255, 255, 255, 0.05)",
                },
              }}
              onClick={() => toggleGroup(groupName)}
            >
              {openGroups[groupName] ? (
                <KeyboardArrowDownIcon
                  sx={{ fontSize: 20, color: "#16FFFF" }}
                />
              ) : (
                <KeyboardArrowRightIcon
                  sx={{ fontSize: 20, color: "#16FFFF" }}
                />
              )}
              <Typography
                sx={{
                  ml: 1,
                  fontSize: "0.9rem",
                  fontWeight: "medium",
                  textTransform: "capitalize",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  wordBreak: "break-all",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}
              >
                {groupName}
              </Typography>
              <Box
                sx={{
                  ml: 1,
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
                    />
                  ))
                ) : (
                  <Typography
                    sx={{
                      color: "#ffffff",
                      opacity: 0.5,
                      textAlign: "center",
                      p: 2,
                    }}
                  >
                    No items found
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
