import { Box, Avatar, Divider } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function Footer() {
  const theme = useTheme();
  return (
    <Box
      display={"flex"}
      justifyContent={"center"}
      alignItems={"center"}
      flexDirection={"column"}
      py={2}
    >
      <Divider sx={{ width: "100%", bgcolor: theme.palette.ui.borderDark }} />
      <Avatar
        alt="DashAI Logo"
        src="/images/logo.png"
        variant="square"
        sx={{ width: 120, p: 0, mt: 2 }}
      />
    </Box>
  );
}
