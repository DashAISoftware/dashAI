import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import PersonRemoveOutlinedIcon from "@mui/icons-material/PersonRemoveOutlined";

import * as projectsApi from "../../../api/projects";
import { useProjects } from "./ProjectContext";
import { useSession } from "./SessionContext";

// Project roles, as defined in the backend catalog (DashAI/back/auth/catalog.py)
const PROJECT_ROLES = [
  { uid: "owner", name: "Dueño" },
  { uid: "manager", name: "Gestor" },
  { uid: "collaborator", name: "Colaborador" },
  { uid: "reader", name: "Lector" },
];

const MESSAGES = {
  "User not found": "No existe una cuenta activa con ese nickname.",
  "That user is already a member of the project":
    "Esa persona ya es integrante del proyecto.",
  "A project must keep at least one owner":
    "El proyecto debe conservar al menos un dueño.",
  "Only an owner can change who owns the project":
    "Solo un dueño puede dar o quitar el rol de dueño.",
  "You do not have permission to perform this action":
    "No tienes permiso para realizar esta acción.",
};

function toMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && MESSAGES[detail]) return MESSAGES[detail];
  return "No se pudo completar la acción. Inténtalo nuevamente.";
}

/**
 * Members of a project. Anyone in the project sees the list; changing roles,
 * removing and adding people needs ``projects.manage``, and the owner role
 * can only be given or taken by an owner or an administrator. The backend
 * checks the same rules; hiding the controls only avoids useless errors.
 */
export default function ProjectMembers({ project }) {
  const theme = useTheme();
  const { user, can } = useSession();
  const { refresh } = useProjects();
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [newRole, setNewRole] = useState("collaborator");
  const [busy, setBusy] = useState(false);

  const canManage = project.my_permissions.includes("projects.manage");
  const canHandleOwners =
    project.my_role?.uid === "owner" || can("projects.oversee");
  const assignableRoles = PROJECT_ROLES.filter(
    (role) => canHandleOwners || role.uid !== "owner",
  );

  const loadMembers = useCallback(async () => {
    setMembers(await projectsApi.getMembers(project.id));
  }, [project.id]);

  useEffect(() => {
    setError("");
    loadMembers().catch((e) => setError(toMessage(e)));
  }, [loadMembers]);

  // Runs a change, then reloads the members and the project list (the member
  // count, or the project itself if the user left it). After leaving, the
  // members can no longer be read, so only the project list is reloaded
  const run = async (action, { left = false } = {}) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await Promise.all([left ? null : loadMembers(), refresh()]);
      return true;
    } catch (e) {
      setError(toMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const handleAdd = async (event) => {
    event.preventDefault();
    if (!username.trim()) return;
    const added = await run(() =>
      projectsApi.addMember(project.id, username.trim(), newRole),
    );
    if (added) setUsername("");
  };

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {members.map((member) => {
        const isMe = member.user_id === user?.id;
        const isOwner = member.role.uid === "owner";
        const canEditThis = canManage && (canHandleOwners || !isOwner);
        // Anyone can leave; removing others needs projects.manage
        const canRemove = isMe || canEditThis;

        return (
          <Box
            key={member.user_id}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              py: 1,
              borderBottom: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" noWrap>
                {member.social_name}
                {isMe && " (tú)"}
              </Typography>
              <Typography
                variant="caption"
                noWrap
                sx={{ color: theme.palette.text.secondary }}
              >
                @{member.username}
              </Typography>
            </Box>

            {canEditThis ? (
              <TextField
                select
                size="small"
                value={member.role.uid}
                disabled={busy}
                onChange={(event) =>
                  run(() =>
                    projectsApi.changeMemberRole(
                      project.id,
                      member.user_id,
                      event.target.value,
                    ),
                  )
                }
                sx={{ minWidth: 130 }}
              >
                {assignableRoles.map((role) => (
                  <MenuItem key={role.uid} value={role.uid}>
                    {role.name}
                  </MenuItem>
                ))}
              </TextField>
            ) : (
              <Typography
                variant="body2"
                sx={{ color: theme.palette.text.secondary }}
              >
                {member.role.name}
              </Typography>
            )}

            {canRemove && (
              <Tooltip title={isMe ? "Salir del proyecto" : "Quitar"}>
                <span>
                  <IconButton
                    size="small"
                    disabled={busy}
                    aria-label={isMe ? "Salir del proyecto" : "Quitar"}
                    onClick={() =>
                      run(
                        () =>
                          projectsApi.removeMember(project.id, member.user_id),
                        { left: isMe },
                      )
                    }
                  >
                    <PersonRemoveOutlinedIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            )}
          </Box>
        );
      })}

      {canManage && (
        <Box
          component="form"
          onSubmit={handleAdd}
          noValidate
          sx={{ display: "flex", gap: 1, mt: 3, flexWrap: "wrap" }}
        >
          <TextField
            size="small"
            label="Nickname"
            value={username}
            disabled={busy}
            onChange={(event) => setUsername(event.target.value)}
            sx={{ flex: 1, minWidth: 140 }}
          />
          <TextField
            select
            size="small"
            label="Rol"
            value={newRole}
            disabled={busy}
            onChange={(event) => setNewRole(event.target.value)}
            sx={{ minWidth: 130 }}
          >
            {assignableRoles.map((role) => (
              <MenuItem key={role.uid} value={role.uid}>
                {role.name}
              </MenuItem>
            ))}
          </TextField>
          <Button
            type="submit"
            variant="outlined"
            disabled={busy || !username.trim()}
          >
            Agregar
          </Button>
        </Box>
      )}
    </Box>
  );
}

ProjectMembers.propTypes = {
  project: PropTypes.shape({
    id: PropTypes.number.isRequired,
    my_role: PropTypes.shape({ uid: PropTypes.string }),
    my_permissions: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
};
