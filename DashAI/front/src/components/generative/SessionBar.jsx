import { Box, Typography, Avatar } from "@mui/material";
import SessionBox from "./SessionBox";
import NewSession from "./NewSession";
import SearchBar from "./SearchBar";
import { getSessions } from "../../api/session";
import { useEffect, useState } from "react";
import { removeSession } from "../../api/session";

export default function SessionBar() {
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState([]);

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
      setFilteredSessions(data);
    });
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredSessions(sessions);
    } else {
      const filtered = sessions.filter((session) =>
        session.name.toLowerCase().includes(searchQuery.toLowerCase()),
      );
      setFilteredSessions(filtered);
    }
  }, [searchQuery, sessions]);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleSessionDelete = (id) => {
    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );
    removeSession(id).then(() => {
      console.log("Session deleted", id);
    });
  };

  const handleSessionClick = (id) => {
    console.log("Session clicked", id);
  };

  const handleSessionInfo = (id) => {
    console.log("Session info", id);
  };

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
        gap={1}
        flexDirection={"column"}
        overflow={"none"}
      >
        {/* Create a new generative session */}
        <NewSession />
        {/* Search Bar */}
        <SearchBar
          placeholder={"Search"}
          value={searchQuery}
          onChange={handleSearchChange}
        />
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
            p={0.5}
          >
            Sessions{" "}
            {filteredSessions.length !== sessions.length &&
              `(${filteredSessions.length}/${sessions.length})`}
          </Typography>
        </Box>

        {/* Sessions Display */}
        <Box display={"flex"} flexDirection={"column"} overflow={"auto"}>
          {filteredSessions.length > 0 ? (
            filteredSessions.map((session) => (
              <SessionBox
                name={session.name}
                key={session.id}
                id={session.id}
                onClick={() => handleSessionClick(session.id)}
                onDelete={handleSessionDelete}
                onInfo={handleSessionInfo}
              />
            ))
          ) : (
            <Typography
              sx={{
                color: "#ffffff",
                opacity: 0.5,
                textAlign: "center",
                padding: 2,
              }}
            >
              No sessions found
            </Typography>
          )}
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
