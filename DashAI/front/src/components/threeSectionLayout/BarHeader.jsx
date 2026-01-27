import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function BarHeader() {
  const theme = useTheme();
  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="space-between"
      height={"70px"}
      px={2}
      py={1.5}
    ></Box>
  );
}
