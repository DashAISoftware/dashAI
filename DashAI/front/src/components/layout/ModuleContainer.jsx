import { Box } from "@mui/material";

export default function ModuleContainer({ children, ...props }) {
  return (
    <Box
      height="calc(100vh - 74px)"
      width="100%"
      display="flex"
      position="relative"
      data-container="datasets"
      {...props}
    >
      {children}
    </Box>
  );
}
