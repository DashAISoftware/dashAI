import { Box } from "@mui/material";

export default function ModuleContainer({ children, ...props }) {
  return (
    <Box
      sx={{
        height: (t) => `calc(100vh - ${t.layout.dimensions.appBarHeightLg})`,
      }}
      width="100%"
      display="flex"
      data-container="datasets"
      {...props}
    >
      {children}
    </Box>
  );
}
