import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  IconButton,
  TextField,
  CircularProgress,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ChevronRight, Search as SearchIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import SideBar from "../threeSectionLayout/SideBar";
import { getComponents } from "../../api/component";
import ModelListItem from "./model/ModelListItem";

export default function ModelsRightBar({ session, onToggle, onModelClick }) {
  const theme = useTheme();
  const [models, setModels] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const fetchModels = React.useCallback(async () => {
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
  }, [session?.task_name, enqueueSnackbar]);

  useEffect(() => {
    if (session) {
      fetchModels();
    } else {
      setModels([]);
      setFilteredModels([]);
      setSearchQuery("");
    }
  }, [session, fetchModels]);

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
            borderBottom: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6" color="text.primary">
            Available Models
          </Typography>
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

            {/* Models List */}
            <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
              {loading ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100%",
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
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: "text.secondary", textAlign: "center" }}
                  >
                    {searchQuery
                      ? "No models match your search"
                      : "No compatible models found"}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {filteredModels.map((model) => (
                    <ModelListItem
                      key={model.name}
                      model={model}
                      onClick={() => handleModelClick(model)}
                    />
                  ))}
                </Box>
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
