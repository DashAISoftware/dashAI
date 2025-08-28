import { useState, useRef, useEffect } from "react";
import { Box, Typography, TextField } from "@mui/material";
import ItemMenu from "./ItemMenu";

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

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      setIsEditing(false);
      if (editedName.trim() !== name && editedName.trim() !== "") {
        onEdit(editedName);
      } else {
        setEditedName(name);
      }
    }
    if (e.key === "Escape") {
      setIsEditing(false);
      setEditedName(name);
    }
  };

  const handleBlur = (e) => {
    const next = e.relatedTarget;

    if (
      next &&
      (next.closest("#dataset-menu") || next.closest(".MuiMenu-root"))
    ) {
      return;
    }

    setIsEditing(false);
    if (editedName.trim() !== name && editedName.trim() !== "") {
      onEdit(editedName);
    } else {
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
        bgcolor: isSelected ? "rgba(255, 255, 255, 0.05)" : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: "rgba(255, 255, 255, 0.05)",
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
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            width: "100%",
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
                maxWidth: 180,
                fontSize: 14,
                "& .MuiInputBase-input": { fontSize: 14, padding: "2px 6px" },
              }}
            />
          ) : (
            <Typography
              variant="body2"
              noWrap
              sx={{ maxWidth: 180, fontSize: 14 }}
            >
              {editedName}
            </Typography>
          )}
          <Typography
            variant="caption"
            noWrap
            sx={{ maxWidth: 150, fontSize: 10, pl: 1 }}
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
