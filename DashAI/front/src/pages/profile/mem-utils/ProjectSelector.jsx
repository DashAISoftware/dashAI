import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

import CreateProjectDialog from "./CreateProjectDialog";
import { useProjects } from "./ProjectContext";
import { useSession } from "./SessionContext";

// Views whose data belongs to a project; a detail page of one project (such
// as /app/data/datasets/12) makes no sense in another, so switching goes back
// to the section
const PROJECT_SECTIONS = ["/app/data", "/app/models", "/app/generative"];

/**
 * Header control to switch the project the user works in. Managing projects
 * and their members stays in the profile.
 */
export default function ProjectSelector() {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useSession();
  const { projects, currentProject, selectProject } = useProjects();
  const [anchorEl, setAnchorEl] = useState(null);
  const [creating, setCreating] = useState(false);

  if (!user) return null;

  const close = () => setAnchorEl(null);

  const handleSelect = (projectId) => {
    close();
    if (projectId === currentProject?.id) return;
    const section = PROJECT_SECTIONS.find((path) =>
      location.pathname.startsWith(path + "/"),
    );
    if (section) navigate(section);
    selectProject(projectId);
  };

  return (
    <>
      <Button
        variant="outlined"
        size="small"
        onClick={(event) => setAnchorEl(event.currentTarget)}
        startIcon={<FolderOutlinedIcon sx={{ fontSize: 18 }} />}
        endIcon={<KeyboardArrowDownIcon />}
        aria-label="Proyecto actual"
        sx={{
          height: 32,
          maxWidth: { xs: 140, sm: 240 },
          textTransform: "none",
          color: theme.palette.text.primary,
          borderColor: theme.palette.divider,
        }}
      >
        <Box
          component="span"
          sx={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {currentProject?.name ?? "Sin proyecto"}
        </Box>
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={close}
        slotProps={{ paper: { sx: { minWidth: 240, maxWidth: 320 } } }}
      >
        {projects.length === 0 && (
          <Typography
            variant="body2"
            sx={{ px: 2, py: 1, color: theme.palette.text.secondary }}
          >
            Aún no tienes proyectos.
          </Typography>
        )}
        {projects.map((project) => (
          <MenuItem
            key={project.id}
            selected={project.id === currentProject?.id}
            onClick={() => handleSelect(project.id)}
          >
            <ListItemIcon>
              {project.id === currentProject?.id && (
                <CheckIcon fontSize="small" />
              )}
            </ListItemIcon>
            <ListItemText
              primary={project.name}
              secondary={project.my_role?.name}
              primaryTypographyProps={{ noWrap: true }}
            />
          </MenuItem>
        ))}
        <Divider />
        <MenuItem
          onClick={() => {
            close();
            setCreating(true);
          }}
        >
          <ListItemIcon>
            <AddIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Nuevo proyecto" />
        </MenuItem>
        <MenuItem
          onClick={() => {
            close();
            navigate("/app/profile/projects");
          }}
        >
          <ListItemIcon>
            <SettingsOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Gestionar proyectos" />
        </MenuItem>
      </Menu>

      <CreateProjectDialog open={creating} onClose={() => setCreating(false)} />
    </>
  );
}
