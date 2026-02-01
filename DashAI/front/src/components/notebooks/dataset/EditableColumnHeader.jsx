import { useState, useRef, useEffect } from "react";
import { Typography, TextField, Box, Tooltip } from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * Editable column header component that allows users to rename dataset columns.
 *
 * @param {string} columnName - Current name of the column
 * @param {string} columnType - Type of the column (e.g., "Integer", "Text")
 * @param {Function} onRename - Callback function when rename is confirmed (oldName, newName) => Promise
 * @param {boolean} disabled - Whether editing is disabled
 */
export default function EditableColumnHeader({
  columnName,
  columnType,
  onRename,
  disabled = false,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(columnName);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const { t } = useTranslation(["common"]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleEditClick = () => {
    if (disabled) return;
    setEditValue(columnName);
    setError("");
    setIsEditing(true);
  };

  const handleCancel = () => {
    setEditValue(columnName);
    setError("");
    setIsEditing(false);
  };

  const handleConfirm = async () => {
    const newName = editValue.trim();
    if (!newName) {
      setError(t("common:columnNameEmpty"));
      return;
    }
    if (newName === columnName) {
      setIsEditing(false);
      return;
    }
    if (!/^[a-zA-Z0-9_]+$/.test(newName)) {
      setError(t("common:columnNameInvalid"));
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      await onRename(columnName, newName);
      setIsEditing(false);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("common:errorRenamingColumn"),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleConfirm();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  if (isEditing) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
          gap: 0.5,
        }}
      >
        <TextField
          inputRef={inputRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleConfirm}
          size="small"
          error={!!error}
          disabled={isLoading}
          sx={{
            width: "100%",
            "& .MuiInputBase-input": {
              fontSize: "0.875rem",
              paddingY: 0.5,
              textAlign: "center",
            },
          }}
        />
        {error && (
          <Typography
            variant="caption"
            color="error"
            sx={{ fontSize: "0.7rem" }}
          >
            {error}
          </Typography>
        )}
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: "0.7rem" }}
        >
          {isLoading ? t("common:loading") : columnType || t("common:unknown")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        gap: 0.5,
        textAlign: "center",
      }}
    >
      <Tooltip title={!disabled ? t("common:renameColumn") : ""} arrow>
        <Typography
          variant="subtitle2"
          onDoubleClick={!disabled ? handleEditClick : undefined}
          sx={{
            fontWeight: "bold",
            fontSize: "0.875rem",
            cursor: !disabled ? "pointer" : "default",
            transition: "all 0.2s",
            "&:hover": !disabled
              ? {
                  color: "primary.main",
                  textDecoration: "underline",
                }
              : {},
          }}
        >
          {columnName}
        </Typography>
      </Tooltip>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ fontSize: "0.7rem" }}
      >
        {columnType || t("common:unknown")}
      </Typography>
    </Box>
  );
}
