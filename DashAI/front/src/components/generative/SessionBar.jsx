import { Box, Typography, Divider } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import SearchBar from "../threeSectionLayout/SearchBar";
import { useEffect, useState } from "react";
import InfoSessionModal from "./InfoSessionModal";
import Footer from "./Footer";
import SessionList from "./SessionList";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/SideBar";
import BarHeader from "../threeSectionLayout/BarHeader";
import { useTranslation } from "react-i18next";

export default function SessionBar({
  sessions,
  selectedSessionId,
  handleSessionClick,
  handleNewSessionButton,
  handleSessionDelete,
  stepIndex,
}) {
  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const [openSections, setOpenSections] = useState({});
  const { t } = useTranslation(["generative", "common"]);

  useEffect(() => {
    // Initialize all sections as closed
    const taskNames = [
      ...new Set(
        sessions.map((session) => session.task_name || t("common:other")),
      ),
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

  // Group sessions by display_name
  const groupedSessions = filteredSessions?.reduce((groups, session) => {
    const displayName = session.display_name || t("common:other");
    if (!groups[displayName]) {
      groups[displayName] = [];
    }
    groups[displayName].push(session);
    return groups;
  }, {});

  return (
    <SideBar>
      <Box
        display="flex"
        flexDirection="column"
        flex={1}
        justifyContent={"flex-start"}
        minHeight={0}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            pr: 2,
          }}
        >
          <BarHeader />
        </Box>
        <Divider sx={{ width: "100%", bgcolor: "divider" }} />

        <Box
          p={2}
          sx={{ height: "64px", display: "flex", alignItems: "center" }}
        >
          {/* Create new session button */}
          {selectedSessionId ? (
            <NewItemButton
              onClick={handleNewSessionButton}
              title={t("generative:button.createSession")}
            />
          ) : (
            <Typography variant="body1" color="textSecondary">
              {t("generative:label.generativeModule")}
            </Typography>
          )}
        </Box>

        {/* Search Bar */}
        <Box px={2} pb={2} flex={"0 0 auto"}>
          <SearchBar
            placeholder={t("generative:label.searchSessions")}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

        {/* Sessions */}
        <Box
          minHeight={0}
          pb={1}
          overflow="auto"
          sx={{
            flex: 1,
            pl: 2,
            pr: 2,
            pt: 2,
          }}
        >
          {/* Header */}
          <Box display="flex" alignItems="center" py={0.5} px={1} mb={0.5}>
            <FolderIcon sx={{ color: "#16FFFF", mr: 1, fontSize: 20 }} />
            <Typography color="text.primary">
              {t("generative:label.sessions")}
            </Typography>
            <Box
              sx={{
                ml: 1,
                bgcolor: theme.palette.ui.border,
                color: "text.primary",
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
    </SideBar>
  );
}
