import { Box, Typography } from "@mui/material";

export default function BarHeader() {
  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="space-between"
      height={"70px"}
      px={2}
      py={1.5}
    >
      <Typography
        variant="h6"
        sx={{
          fontWeight: "bold",
          "& span": { color: "#16FFFF" },
        }}
      >
        <span>D</span>a<span>sh</span>
      </Typography>
    </Box>
  );
}
