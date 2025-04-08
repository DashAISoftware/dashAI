import { Box, Typography, Divider, Collapse } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FolderIcon from "@mui/icons-material/Folder";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import SearchBar from "./SearchBar";
import SessionBox from "./SessionBox";
import Avatar from "@mui/material/Avatar";
import { getSessions } from "../../api/session";
import { useEffect, useState } from "react";
import { removeSession } from "../../api/session";
import InfoSessionModal from "./InfoSessionModal";

export default function SessionBar() {
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const [openSections, setOpenSections] = useState({});

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
      setFilteredSessions(data);

      // Initialize all sections as open
      const taskNames = [
        ...new Set(data.map((session) => session.task_name || "Other")),
      ];
      const initialOpenState = {};
      taskNames.forEach((task) => {
        initialOpenState[task] = true;
      });
      setOpenSections(initialOpenState);
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
  const groupedSessions = filteredSessions.reduce((groups, session) => {
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
      height="auto"
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
      <Box>
        {/* Header */}
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
        <Divider sx={{ width: "100%", bgcolor: "#252836" }} />

        {/* Create new session button */}
        <Box px={2} py={1}>
          <Box
            sx={{
              bgcolor: "#374151",
              color: "white",
              borderRadius: 1,
              mt: 1,
              py: 1,
              px: 2,
              display: "flex",
              alignItems: "center",
              cursor: "pointer",
              "&:hover": {
                bgcolor: "#475569",
              },
              height: "45px",
            }}
          >
            <AddIcon sx={{ mr: 1 }} />
            <Typography>New session</Typography>
          </Box>
        </Box>

        {/* Search Bar */}
        <Box px={2} py={1}>
          <SearchBar
            placeholder={"Search"}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>

        {/* Sessions */}
        <Box px={2} py={1}>
          {/* Sessions Header */}
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
              {filteredSessions.length}
            </Box>
          </Box>

          {/* Sessions Display Grouped by Task */}
          <Box display={"flex"} flexDirection={"column"}>
            {Object.keys(groupedSessions).length > 0 ? (
              Object.entries(groupedSessions).map(
                ([taskName, taskSessions]) => (
                  <Box key={taskName} mb={1}>
                    {/* Task Section Header */}
                    <Box
                      display="flex"
                      alignItems="center"
                      sx={{
                        cursor: "pointer",
                        py: 0.5,
                        px: 1,
                        borderRadius: 1,
                        "&:hover": {
                          bgcolor: "rgba(255, 255, 255, 0.05)",
                        },
                      }}
                      onClick={() => toggleSection(taskName)}
                    >
                      {openSections[taskName] ? (
                        <KeyboardArrowDownIcon
                          sx={{ fontSize: 20, color: "#16FFFF" }}
                        />
                      ) : (
                        <KeyboardArrowRightIcon
                          sx={{ fontSize: 20, color: "#16FFFF" }}
                        />
                      )}
                      <Typography
                        sx={{
                          ml: 1,
                          fontSize: "0.9rem",
                          fontWeight: "medium",
                          textTransform: "capitalize",
                        }}
                      >
                        {taskName}
                      </Typography>
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
                        {taskSessions.length}
                      </Box>
                    </Box>

                    {/* Task Sessions */}
                    <Collapse in={openSections[taskName]} timeout="auto">
                      <Box pl={2}>
                        {taskSessions.map((session) => (
                          <SessionBox
                            name={session.name}
                            modelName={session.model_name}
                            key={session.id}
                            id={session.id}
                            onClick={() => handleSessionClick(session.id)}
                            onDelete={handleSessionDelete}
                            onInfo={handleSessionInfo}
                          />
                        ))}
                      </Box>
                    </Collapse>
                  </Box>
                ),
              )
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
      </Box>

      {/* Footer */}
      <Box
        display={"flex"}
        justifyContent={"center"}
        alignItems={"center"}
        flexDirection={"column"}
        py={2}
      >
        <Divider sx={{ width: "100%", bgcolor: "#252836" }} />
        <Avatar
          alt="DashAI Logo"
          src="/images/logo.png"
          variant="square"
          sx={{ width: 120, p: 0, mt: 2 }}
        />
      </Box>
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
