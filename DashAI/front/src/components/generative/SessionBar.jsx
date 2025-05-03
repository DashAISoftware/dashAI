import { Box, Typography, Divider } from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import SearchBar from "./SearchBar";
import { useEffect, useState } from "react";
import InfoSessionModal from "./InfoSessionModal";
import Footer from "./Footer";
import SessionList from "./SessionList";
import NewSessionButton from "./NewSessionButton";
import SessionBarHeader from "./SessionBarHeader";

export default function SessionBar({
  sessions,
  setSessions,
  selectedSessionId,
  handleSessionClick,
  handleNewSessionButton,
  handleSessionDelete,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const [openSections, setOpenSections] = useState({});

  useEffect(() => {
    // Initialize all sections as closed
    const taskNames = [
      ...new Set(sessions.map((session) => session.task_name || "Other")),
    ];
    const initialOpenState = {};
    taskNames.forEach((task) => {
      initialOpenState[task] = false;
    });
    setOpenSections(initialOpenState);
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

  const handleSessionInfo = (id) => {
    // Find the session with the matching id
    const session = sessions.find((session) => session.id === id);
    if (session) {
      setSelectedInfoSession(session);
    }
  };

  const toggleSection = (taskName) => {
    setOpenSections((prev) => ({
      ...prev,
      [taskName]: !prev[taskName],
    }));
  };

  // Group sessions by task_name
  const groupedSessions = filteredSessions?.reduce((groups, session) => {
    const taskName = session.task_name || "Other";
    if (!groups[taskName]) {
      groups[taskName] = [];
    }
    groups[taskName].push(session);
    return groups;
  }, {});

  return (
    <Box
      width="285px"
      height="100%"
      borderRadius={2}
      display={"flex"}
      flexDirection={"column"}
      justifyContent={"space-between"}
      sx={{
        bgcolor: "#030712",
        color: "white",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid #252836",
      }}
    >
      <Box
        display="flex"
        flexDirection="column"
        flex={1}
        justifyContent={"flex-start"}
        minHeight={0}
      >
        {/* Header */}
        <SessionBarHeader />
        <Divider sx={{ width: "100%", bgcolor: "#252836" }} />

        {/* Create new session button */}
        <NewSessionButton onClick={handleNewSessionButton} />

        {/* Search Bar */}
        <Box px={2} py={1} flex={"0 0 auto"}>
          <SearchBar
            placeholder={"Search"}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>

        {/* Sessions */}
        <Box px={2} py={1} flex={1} minHeight={0} overflow="auto">
          {/* Header */}
          <Box display="flex" alignItems="center" pb={1}>
            <FolderIcon sx={{ color: "#16FFFF", mr: 1, fontSize: 20 }} />
            <Typography>Sessions</Typography>
            <Box
              sx={{
                ml: 1,
                bgcolor: "#374151",
                color: "white",
                borderRadius: "50%",
                width: 20,
                height: 20,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
              }}
            >
              {filteredSessions?.length}
            </Box>
          </Box>
          {/* Sessions Display Grouped by Task */}
          <Box>
            <SessionList
              selectedSessionId={selectedSessionId}
              groupedSessions={groupedSessions}
              openSections={openSections}
              handleSessionClick={handleSessionClick}
              handleSessionDelete={handleSessionDelete}
              handleSessionInfo={handleSessionInfo}
              toggleSection={toggleSection}
            />
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Footer />
      {/* Session Info Modal */}
      {selectedInfoSession && (
        <InfoSessionModal
          sessionData={selectedInfoSession}
          open={!!selectedInfoSession}
          onClose={() => setSelectedInfoSession(null)}
        />
      )}
    </Box>
  );
}
