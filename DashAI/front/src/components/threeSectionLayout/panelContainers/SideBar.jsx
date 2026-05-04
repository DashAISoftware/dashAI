import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function SideBar({ children }) {
  const theme = useTheme();

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
        borderBottom: `0.1px solid ${theme.palette.divider}`,
      }}
    >
      {children}
    </Box>
  );
}
