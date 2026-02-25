import { Box, Typography, Divider, IconButton } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import SearchBar from "../threeSectionLayout/SearchBar";
import { useEffect, useState } from "react";
import InfoSessionModal from "./InfoSessionModal";
import GroupedCollapsibleList from "../threeSectionLayout/GroupedCollapsibleList";
import Footer from "./Footer";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import BarHeader from "../threeSectionLayout/BarHeader";
import { ChevronLeft } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

export default function SessionBar({
  tasks,
  sessions,
  selectedSessionId,
  handleSessionClick,
  handleNewSessionButton,
  handleSessionDelete,
  stepIndex,
  onToggle,
}) {
  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const [openSections, setOpenSections] = useState({});
  const { t } = useTranslation(["generative", "common"]);

  console.log(tasks);
  console.log(sessions);

  // Create a map of task_name to display_name for quick lookup
  const taskDisplayNameMap =
    tasks?.reduce((map, task) => {
      map[task.name] = task.display_name;
      return map;
    }, {}) || {};

  useEffect(() => {
    // Initialize all sections as closed based on unique task display names
    const uniqueDisplayNames = [
      ...new Set(
        sessions.map(
          (session) =>
            taskDisplayNameMap[session.task_name] || t("common:other"),
        ),
      ),
    ];
    const initialOpenState = {};
    uniqueDisplayNames.forEach((displayName) => {
      initialOpenState[displayName] = false;
    });
    setOpenSections(initialOpenState);
  }, [sessions, tasks]);

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

  // Group sessions by task display_name
  const groupedSessions = filteredSessions?.reduce((groups, session) => {
    // Get the display name from the task using the session's task_name
    const displayName =
      taskDisplayNameMap[session.task_name] || t("common:other");

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
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronLeft />
          </IconButton>
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
        <GroupedCollapsibleList
          groups={groupedSessions}
          selectedItemId={selectedSessionId}
          onItemClick={handleSessionClick}
          onItemDelete={handleSessionDelete}
          //onItemEdit={editSession} TODO: Edit session functionality to be implemented in the future
          onItemInfo={handleSessionInfo}
          title={t("common:generative")}
          Icon={FolderIcon}
          initialOpenGroups={openSections}
        />
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
