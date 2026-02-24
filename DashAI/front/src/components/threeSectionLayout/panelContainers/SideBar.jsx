import { Box } from "@mui/material";

export default function SideBar({ children }) {
  return (
    <Box
      width="100%"
      height="100%"
      // borderRadius={2}
      display="flex"
      flexDirection="column"
      justifyContent="space-between"
      sx={{
        bgcolor: "background.box",
        color: "white",
        borderTop: "0.1px solid",
        borderBottom: "0.1px solid",
        borderColor: "grey.600",
      }}
    >
      {children}
    </Box>
  );
}
