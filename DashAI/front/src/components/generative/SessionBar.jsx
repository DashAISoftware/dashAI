import { Box, Typography, Divider } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useNavigate } from "react-router-dom";
import FolderIcon from "@mui/icons-material/Folder";
import SearchBar from "../threeSectionLayout/SearchBar";
import { useEffect, useState } from "react";
import InfoSessionModal from "./InfoSessionModal";
import GroupedCollapsibleList from "../threeSectionLayout/GroupedCollapsibleList";
import Footer from "../threeSectionLayout/Footer";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useTranslation } from "react-i18next";
import { useGenerative } from "./GenerativeContext";

export default function SessionBar({ onToggle }) {
  const theme = useTheme();
  const navigate = useNavigate();
  const { tasks, sessions, selectedSessionId, deleteSessionById, editSession } =
    useGenerative();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const [openSections, setOpenSections] = useState({});
  const { t } = useTranslation(["generative", "common"]);

  const SEARCH_THRESHOLD = 10;

  useEffect(() => {
    if (sessions.length <= SEARCH_THRESHOLD) setSearchQuery("");
  }, [sessions.length]);

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
    setOpenSections((prev) => {
      // Only update if display names have changed
      const prevKeys = Object.keys(prev).sort().join(",");
      const newKeys = Object.keys(initialOpenState).sort().join(",");
      if (prevKeys === newKeys) return prev;
      return initialOpenState;
    });
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

  const handleNewSessionButton = () => {
    navigate("/app/generative");
  };

  const handleSessionClick = (sessionId) => {
    navigate(`/app/generative/sessions/${sessionId}`);
  };

  const handleSessionDelete = async (id) => {
    const wasSelected = id === selectedSessionId;
    const ok = await deleteSessionById(id);
    if (ok && wasSelected) {
      navigate("/app/generative");
    }
  };

  const getSessionDeleteConfirmationContent = (session) =>
    t(
      "generative:label.confirmDeleteSession",
      'Are you sure you want to delete the session "{{name}}"? This action cannot be undone.',
      { name: session.name },
    );

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

  // Sort grouped sessions to maintain consistent order
  const sortedGroupedSessions = groupedSessions
    ? Object.keys(groupedSessions)
        .sort()
        .reduce((sorted, key) => {
          sorted[key] = groupedSessions[key];
          return sorted;
        }, {})
    : {};

  return (
    <SideBar>
      <Box
        display="flex"
        flexDirection="column"
        flex={1}
        justifyContent={"flex-start"}
        minHeight={0}
      >
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
        {sessions.length > SEARCH_THRESHOLD && (
          <Box px={2} pb={2} flex={"0 0 auto"}>
            <SearchBar
              placeholder={t("generative:label.searchSessions")}
              value={searchQuery}
              onChange={handleSearchChange}
            />
          </Box>
        )}

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

        {/* Sessions */}
        <GroupedCollapsibleList
          groups={sortedGroupedSessions}
          selectedItemId={selectedSessionId}
          onItemClick={handleSessionClick}
          onItemDelete={handleSessionDelete}
          onItemEdit={editSession}
          onItemInfo={handleSessionInfo}
          title={t("common:generative")}
          Icon={FolderIcon}
          initialOpenGroups={openSections}
          getItemDescription={(session) => session.model_name}
          getDeleteConfirmationContent={getSessionDeleteConfirmationContent}
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
