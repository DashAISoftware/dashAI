import { Box, Typography } from "@mui/material";
import DatasetMenu from "./DatasetMenu";

export default function DatasetBox({
  isSelected,
  name,
  description,
  id,
  onClick,
  onDelete,
  onInfo,
}) {
  return (
    <Box
      sx={{
        width: "100%",
        height: "50px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderRadius: 1,
        cursor: isSelected ? "default" : "pointer",
        bgcolor: isSelected ? "rgba(255, 255, 255, 0.05)" : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: isSelected
            ? "rgba(255, 255, 255, 0.05)"
            : "rgba(255, 255, 255, 0.05)",
        },
      }}
      onClick={isSelected ? undefined : onClick}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          width: "100%",
        }}
      >
        <Box>
          <Typography
            variant="body2"
            noWrap
            sx={{ maxWidth: 180, fontSize: 14 }}
          >
            {name ? name : "Untitled Session"}
          </Typography>
          <Typography
            variant="caption"
            noWrap
            sx={{ maxWidth: 150, fontSize: 10, pl: 1 }}
          >
            {description ? description : ""}
          </Typography>
        </Box>
      </Box>
      <DatasetMenu datasetId={id} onInfo={onInfo} onDelete={onDelete} />
    </Box>
  );
}
