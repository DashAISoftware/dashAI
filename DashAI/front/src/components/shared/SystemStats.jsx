import React, { useState, useEffect, useRef } from "react";
import { Box, IconButton, Typography, Paper } from "@mui/material";
import MemoryIcon from "@mui/icons-material/Memory";
import api from "../../api/api";

const SystemStats = () => {
  const [stats, setStats] = useState(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({
    x: window.innerWidth - 70,
    y: 20,
  });
  const dragRef = useRef(null);
  const offset = useRef({ x: 0, y: 0 });
  const wsRef = useRef(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    if (!open) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const ws = new WebSocket(`${api.defaults.baseURL}/v1/info/ws/system`);
    wsRef.current = ws;

    ws.onmessage = (event) => setStats(JSON.parse(event.data));

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => ws.close();
  }, [open]);

  const handleMouseDown = (e) => {
    draggingRef.current = false;
    offset.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleMouseMove = (e) => {
    draggingRef.current = true;
    setPosition({
      x: e.clientX - offset.current.x,
      y: e.clientY - offset.current.y,
    });
  };

  const handleMouseUp = (e) => {
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  const handleClick = () => {
    if (!draggingRef.current) setOpen(!open);
  };

  const paperLeft =
    position.x + 40 + 300 > window.innerWidth
      ? position.x - 300
      : position.x + 40;

  return (
    <Box
      ref={dragRef}
      sx={{
        position: "fixed",
        left: position.x,
        top: position.y,
        zIndex: 9999,
      }}
    >
      <IconButton
        color="primary"
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        sx={{
          color: "white",
          width: 36,
          height: 36,
          bgcolor: "primary.main",
          "&:hover": { bgcolor: "primary.dark" },
        }}
      >
        <MemoryIcon />
      </IconButton>

      {open && (
        <Paper
          elevation={3}
          sx={{
            position: "absolute",
            left: paperLeft - position.x,
            top: 0,
            p: 2,
            width: 300,
            maxHeight: 400,
            overflowY: "auto",
            bgcolor: "#2E3037",
          }}
        >
          {stats ? (
            <>
              <Typography>
                CPU Usage: {stats.cpu_usage_percent.toFixed(1)}%
              </Typography>
              <Typography>
                RAM: {stats.ram_used_GB.toFixed(1)} /{" "}
                {stats.ram_total_GB.toFixed(1)} GB (
                {stats.ram_usage_percent.toFixed(1)}%)
              </Typography>
              {stats.gpu_devices.map((gpu) => (
                <Box
                  key={gpu.id}
                  sx={{
                    mt: 1,
                    p: 1,
                    border: "1px solid #a7a7a7ff",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="subtitle1">{gpu.name}</Typography>
                  <Typography>Load: {gpu.load_percent.toFixed(1)}%</Typography>
                  <Typography>
                    VRAM: {gpu.vram_used_GB.toFixed(2)} /{" "}
                    {gpu.vram_total_GB.toFixed(1)} GB
                  </Typography>
                  <Typography>
                    Free VRAM: {gpu.vram_free_GB.toFixed(2)} GB
                  </Typography>
                  <Typography>
                    Temp: {gpu.temperature_C.toFixed(1)} °C
                  </Typography>
                </Box>
              ))}
            </>
          ) : (
            <Typography>Loading...</Typography>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default SystemStats;
