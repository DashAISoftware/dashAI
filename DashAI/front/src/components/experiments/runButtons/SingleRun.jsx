import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { PlayArrow } from "@mui/icons-material";
import { CircularProgress } from "@mui/material";

export default function SingleRun({ run, onRun }) {
  const [isStarting, setIsStarting] = useState(false);
  const isRunning = run.status === "Started" || run.status === "Delivered";

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
      label="Run"
      onClick={handleClick}
      disabled={isStarting || isRunning}
    />
  );
}
