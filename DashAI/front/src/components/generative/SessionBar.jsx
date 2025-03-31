import React from "react";
import { Box, Typography, Avatar } from "@mui/material";
import SessionBox from "./SessionBox";
import NewSession from "./NewSession";
import SearchBar from "./SearchBar";

export default function SessionBar({ sessions }) {
  return (
    <Box
      width={"287px"}
      height={"auto"}
      p={2}
      bgcolor={"#161925"}
      borderRadius={2}
      display={"flex"}
      flexDirection={"column"}
      gap={1}
      justifyContent={"space-between"}
      overflow={"none"}
    >
      <Box
        display={"flex"}
        justifyContent={"space-between"}
        flexDirection={"column"}
        overflow={"none"}
      >
        {/* Create a new generative session */}
        <NewSession />
        {/* Search Bar */}
        <SearchBar placeholder={"Search"} />
        {/* Sessions Header */}
        <Box
          display={"flex"}
          justifyContent={"space-between"}
          alignItems={"center"}
          mt={2}
          mb={1}
        >
          <Typography
            display={"flex"}
            flexDirection={"column"}
            justifyContent={"center"}
            sx={{ opacity: "0.5" }}
          >
            Sessions
          </Typography>
        </Box>

        {/* Sessions Display */}
        <Box display={"flex"} flexDirection={"column"} overflow={"auto"}>
          {sessions.map((session) => {
            return <SessionBox name={session.name} key={session.id} />;
          })}
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
  );
}
