import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  IconButton,
  TextField,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Divider,
} from "@mui/material";
import {
  ChevronRight,
  Science as ScienceIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { useSnackbar } from "notistack";
import SideBar from "../threeSectionLayout/SideBar";
import { getComponents } from "../../api/component";

export default function ModelsRightBar({ session, onToggle, onModelClick }) {
  const [models, setModels] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // Fetch compatible models when session changes
  useEffect(() => {
    if (session) {
      fetchModels();
    } else {
      setModels([]);
      setFilteredModels([]);
      setSearchQuery("");
    }
  }, [session]);

  // Filter models based on search
  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredModels(models);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredModels(
        models.filter(
          (model) =>
            (model.display_name || model.name).toLowerCase().includes(query) ||
            (model.metadata?.description || "").toLowerCase().includes(query),
        ),
      );
    }
  }, [searchQuery, models]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const response = await getComponents({
        selectTypes: ["Model"],
        relatedComponent: session.task_name,
      });
      setModels(response);
      setFilteredModels(response);
    } catch (error) {
      console.error("Error fetching models:", error);
      enqueueSnackbar("Error fetching compatible models", {
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleModelClick = (model) => {
    if (onModelClick) {
      onModelClick(model);
    }
  };

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            borderBottom: "1px solid #333",
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6">Available Models</Typography>
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronRight />
          </IconButton>
        </Box>

        {/* Content */}
        {!session ? (
          <Box
            sx={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "text.secondary", textAlign: "center" }}
            >
              Select a session to view available models.
            </Typography>
          </Box>
        ) : (
          <>
            {/* Search Box */}
            <Box sx={{ p: 2, flexShrink: 0 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <SearchIcon sx={{ mr: 1, color: "text.secondary" }} />
                    ),
                  },
                }}
              />
            </Box>

            <Divider />

            {/* Models List */}
            <Box sx={{ flex: 1, overflow: "auto" }}>
              {loading ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100%",
                    p: 2,
                  }}
                >
                  <CircularProgress size={32} />
                </Box>
              ) : filteredModels.length === 0 ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100%",
                    p: 2,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {searchQuery
                      ? "No models match your search"
                      : "No compatible models found"}
                  </Typography>
                </Box>
              ) : (
                <List sx={{ p: 0 }}>
                  {filteredModels.map((model) => (
                    <React.Fragment key={model.name}>
                      <ListItemButton
                        onClick={() => handleModelClick(model)}
                        sx={{
                          py: 1.5,
                          "&:hover": {
                            backgroundColor: "action.hover",
                          },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          <ScienceIcon color="primary" />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" fontWeight="medium">
                              {model.display_name || model.name}
                            </Typography>
                          }
                          secondary={
                            model.metadata?.description ? (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{
                                  display: "-webkit-box",
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: "vertical",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                }}
                              >
                                {model.metadata.description}
                              </Typography>
                            ) : null
                          }
                        />
                      </ListItemButton>
                      <Divider />
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Box>
          </>
        )}
      </Box>
    </SideBar>
  );
}

ModelsRightBar.propTypes = {
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onToggle: PropTypes.func.isRequired,
  onModelClick: PropTypes.func,
};
