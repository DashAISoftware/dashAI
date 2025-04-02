import {
  Box,
  Typography,
  TextField,
  Grid,
  Select,
  MenuItem,
} from "@mui/material";
import React from "react";
import AddCardIcon from "@mui/icons-material/AddCard";
import { Search } from "@mui/icons-material";
import Paper from "@mui/material/Paper";
import InputBase from "@mui/material/InputBase";
import IconButton from "@mui/material/IconButton";
import SearchIcon from "@mui/icons-material/Search";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import Button from "@mui/material/Button";
import Avatar from "@mui/material/Avatar";

function Generative() {
  return (
    <Box
      display={"flex"}
      justifyContent={"space-between"}
      gap={"5px"}
      height={"800px"}
      flexGrow={1}
      p={1.5}
    >
      {/* Left Side */}
      <Box
        width={"287px"}
        height={"auto"}
        p={2}
        bgcolor={"#161925"}
        borderRadius={2}
        display={"flex"}
        flexDirection={"column"}
        gap={2}
        justifyContent={"space-between"}
      >
        <Box>
          <Box display={"flex"} justifyContent={"space-between"}>
            <Typography
              display={"flex"}
              flexDirection={"column"}
              justifyContent={"center"}
              sx={{ opacity: "0.5" }}
            >
              First Generative...
            </Typography>

            <Box>
              <IconButton type="button" sx={{ p: "10px" }}>
                <SearchIcon />
              </IconButton>
              <IconButton type="button" sx={{ p: "10px" }}>
                <AddCardIcon />
              </IconButton>
            </Box>
          </Box>
          {/* These should be components */}
          <Box>
            <Typography>Today</Typography>
            <Button
              sx={{
                width: "100%",
                height: "30px",
                display: "flex",
                justifyContent: "space-between",
                textTransform: "none",
              }}
              borderRadius={1}
              p={0.5}
              disabled
            >
              <Box
                display={"flex"}
                flexDirection={"column"}
                alignItems={"center"}
                justifyContent={"center"}
                gap={0.5}
              >
                <Typography
                  variant="h1"
                  sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
                >
                  First Generative Run
                </Typography>
              </Box>
              <IconButton>
                <MoreHorizIcon />
              </IconButton>
            </Button>
            <Button
              sx={{
                width: "100%",
                height: "30px",
                display: "flex",
                justifyContent: "space-between",
                textTransform: "none",
              }}
              borderRadius={1}
              p={0.5}
            >
              <Box
                display={"flex"}
                flexDirection={"column"}
                alignItems={"center"}
                justifyContent={"center"}
                gap={0.5}
              >
                <Typography
                  variant="h1"
                  sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
                >
                  Second Generative Run
                </Typography>
              </Box>
              <IconButton>
                <MoreHorizIcon />
              </IconButton>
            </Button>
            <Button
              sx={{
                width: "100%",
                height: "30px",
                display: "flex",
                justifyContent: "space-between",
                textTransform: "none",
              }}
              borderRadius={1}
              p={0.5}
            >
              <Box
                display={"flex"}
                flexDirection={"column"}
                alignItems={"center"}
                justifyContent={"center"}
                gap={0.5}
              >
                <Typography
                  variant="h1"
                  sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
                >
                  Third Generative Run
                </Typography>
              </Box>
              <IconButton>
                <MoreHorizIcon />
              </IconButton>
            </Button>
            <Typography>Last Week</Typography>
            <Button
              sx={{
                width: "100%",
                height: "30px",
                display: "flex",
                justifyContent: "space-between",
                textTransform: "none",
              }}
              borderRadius={1}
              p={0.5}
            >
              <Box
                display={"flex"}
                flexDirection={"column"}
                alignItems={"center"}
                justifyContent={"center"}
                gap={0.5}
              >
                <Typography
                  variant="h1"
                  sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
                >
                  Another Generative Run
                </Typography>
              </Box>
              <IconButton>
                <MoreHorizIcon />
              </IconButton>
            </Button>
          </Box>
        </Box>

        <Box display={"flex"} justifyContent={"center"}>
          <Avatar
            alt="DashAI Logo"
            src="/images/logo.png"
            variant="square"
            sx={{ width: 120, p: 0, mr: 3, my: 1, mt: 2 }}
          />
        </Box>
      </Box>

      {/* Chat */}
      <Box width={"1063px"} height={"auto"} p={2} pt={0} pb={4}>
        <Box
          bgcolor={"#212121"}
          width={"100%"}
          height={"100%"}
          borderRadius={2}
        ></Box>
        {children}
      </Box>

      {/* Right Side */}
      <Box
        width={"502px"}
        height={"auto"}
        borderRadius={2}
        p={2}
        bgcolor={"#161925"}
      >
        <Typography>Parameters</Typography>
        <TextField
          id="num inference step"
          label="num inference step"
          variant="outlined"
          fullWidth
          margin="normal"
          size="small"
        />
        <TextField
          id="guidance scale"
          label="guidance scale"
          variant="outlined"
          fullWidth
          margin="normal"
          size="small"
        />
        <TextField
          id="batch size"
          label="batch size"
          variant="outlined"
          fullWidth
          margin="normal"
          size="small"
        />
        <TextField
          id="seed"
          label="seed"
          variant="outlined"
          fullWidth
          margin="normal"
          size="small"
        />

        <TextField
          select
          label="device"
          variant="outlined"
          fullWidth
          margin="normal"
          defaultValue="auto"
          size="small"
        >
          <MenuItem value="CPU">CPU</MenuItem>
          <MenuItem value="GPU">GPU</MenuItem>
          <MenuItem value="auto">auto</MenuItem>
        </TextField>

        <TextField
          select
          label="sampler"
          variant="outlined"
          fullWidth
          margin="normal"
          defaultValue="Euler"
          size="small"
        >
          <MenuItem value="Euler">Euler</MenuItem>
        </TextField>

        <Grid container spacing={2}>
          <Grid item xs={6}>
            <TextField
              label="width"
              variant="outlined"
              fullWidth
              margin="normal"
              size="small"
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              label="height"
              variant="outlined"
              fullWidth
              margin="normal"
              size="small"
            />
          </Grid>
        </Grid>

        <Button variant="contained" fullWidth color="primary" sx={{ mt: 2 }}>
          Edit
        </Button>
      </Box>
    </Box>
  );
}

export default Generative;
