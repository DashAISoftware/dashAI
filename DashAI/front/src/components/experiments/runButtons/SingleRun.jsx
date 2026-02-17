import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { PlayArrow } from "@mui/icons-material";
import { CircularProgress } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function SingleRun({ run, onRun }) {
  const [isStarting, setIsStarting] = useState(false);
  const isRunning = run.status === 1 || run.status === 2; // Delivered or Started
  const { t } = useTranslation("experiments");

  const handleClick = async () => {
    setIsStarting(true);
    try {
      await onRun(run);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <GridActionsCellItem
      icon={
        isStarting || isRunning ? <CircularProgress size={18} /> : <PlayArrow />
      }
      label={t("button.run")}
      onClick={handleClick}
      disabled={isStarting || isRunning}
    />
  );
}
