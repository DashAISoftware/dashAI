import {
  Box,
  Typography,
  Button,
  Paper,
  useMediaQuery,
  useTheme,
} from "@mui/material";

export default function OptionBox({
  optionName,
  description,
  onClick,
  Icon = null,
  ...otherProps
}) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.up("md"));

  return (
    <Button
      data-tour="models-task-selection"
      onClick={onClick}
      sx={{
        p: 0,
        m: 1,
        width: "100%",
        height: "100%",
        textAlign: "left",
        textTransform: "none",
        borderRadius: 2,
      }}
      {...otherProps}
    >
      <Paper
        elevation={2}
        sx={{
          p: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: matches ? "row" : "column",
          alignItems: "center",
          justifyContent: matches ? "space-between" : "center",
          textAlign: matches ? "left" : "center",
          "&:hover": {
            backgroundColor: "#1e1e1e",
          },
        }}
      >
        {Icon && (
          <Box md={3}>
            <Icon color="primary" fontSize="large" sx={{ width: "100%" }} />
          </Box>
        )}
        <Box
          sx={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-evenly",
            alignItems: matches ? "flex-start" : "center",
            gap: 1,
          }}
        >
          <Typography variant="h6" sx={{ mb: 1 }}>
            {optionName}
          </Typography>
          <Typography variant="caption" component="p">
            {description}
          </Typography>
        </Box>
      </Paper>
    </Button>
  );
}
