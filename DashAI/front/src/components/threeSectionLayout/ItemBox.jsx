import { useState, useRef, useEffect } from "react";
import { Box, Typography, TextField } from "@mui/material";
import ItemMenu from "./ItemMenu";
import { useTheme } from "@mui/material/styles";

export default function ItemBox({
  isSelected,
  name,
  description,
  id,
  onClick,
  onDelete,
  onEdit,
  onInfo,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(name);
  const inputRef = useRef(null);
  const theme = useTheme();

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleKeyDown = async (e) => {
    if (e.key === "Enter") {
      if (editedName.trim() !== name) {
        try {
          await onEdit(editedName.trim());
          setIsEditing(false);
        } catch (error) {
          setEditedName(name);
          setIsEditing(false);
        }
      } else {
        setIsEditing(false);
        setEditedName(name);
      }
    }
    if (e.key === "Escape") {
      setIsEditing(false);
      setEditedName(name);
    }
  };

  const handleBlur = async (e) => {
    const next = e.relatedTarget;

    if (
      next &&
      (next.closest("#dataset-menu") || next.closest(".MuiMenu-root"))
    ) {
      return;
    }

    if (editedName.trim() !== name) {
      try {
        await onEdit(editedName.trim());
        setIsEditing(false);
      } catch (error) {
        // If edit fails, restore original name and exit editing mode
        setEditedName(name);
        setIsEditing(false);
      }
    } else {
      setIsEditing(false);
      setEditedName(name);
    }
  };

  return (
    <Box
      sx={{
        width: "100%",
        height: "50px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderRadius: 1,
        cursor: isSelected || isEditing ? "default" : "pointer",
        bgcolor: isSelected ? theme.palette.action.selected : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: isSelected
            ? theme.palette.action.selected
            : theme.palette.action.hover,
        },
      }}
      onClick={isSelected || isEditing ? undefined : onClick}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          width: "100%",
          minWidth: 0,
          flex: 1,
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            width: "100%",
            minWidth: 0, // Permite que el contenido se encoja
          }}
        >
          {isEditing ? (
            <TextField
              inputRef={inputRef}
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleBlur}
              size="small"
              variant="outlined"
              sx={{
                width: "100%",
                fontSize: 14,
                "& .MuiInputBase-input": { fontSize: 14, padding: "2px 6px" },
              }}
            />
          ) : (
            <Typography
              variant="body2"
              color="text.primary"
              noWrap
              sx={{ fontSize: 14 }}
            >
              {editedName}
            </Typography>
          )}
          <Typography
            variant="caption"
            color="text.secondary"
            noWrap
            sx={{ fontSize: 10, pl: 1 }}
          >
            {description ? description : ""}
          </Typography>
        </Box>
      </Box>
      <ItemMenu
        itemId={id}
        onInfo={onInfo}
        onDelete={onDelete}
        onEdit={handleEdit}
      />
    </Box>
  );
}
