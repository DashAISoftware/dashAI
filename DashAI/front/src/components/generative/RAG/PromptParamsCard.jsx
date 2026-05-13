import { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Collapse,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { ViewList as ViewListIcon, Info as InfoIcon, ExpandMore as ExpandMoreIcon } from "@mui/icons-material";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import PromptBody from "../../../pages/generative/simplified-RAG/components/PromptBody";

export default function PromptParamsCard({
  promptId,
  setPromptId,
  onTokenCountChange,
}) {
  const navigate = useNavigate();
  const goToPromptsDetail = () => navigate("/app/generative/rag/prompts");
  const { t } = useTranslation(["generative"]);
  const [showDescription, setShowDescription] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <Card sx={{ backgroundColor: "background.paper" }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Prompt</Typography>
            <Box>
              <Tooltip title={t("generative:simplifiedRag.prompt.descriptionToggle") || "Description"}>
                <IconButton
                  size="small"
                  onClick={() => setShowDescription((s) => !s)}
                  aria-label="prompt-info"
                  sx={{ color: "text.secondary" }}
                >
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={t("generative:simplifiedRag.prompt.openPrompts")}>
                <IconButton size="small" onClick={goToPromptsDetail} aria-label="open-prompt-library">
                  <ViewListIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={isExpanded ? (t("generative:simplifiedRag.prompt.collapse") || "Collapse") : (t("generative:simplifiedRag.prompt.expand") || "Expand")}>
                <IconButton
                  size="small"
                  onClick={() => setIsExpanded((s) => !s)}
                  aria-label="toggle-prompt-card"
                >
                  <ExpandMoreIcon
                    fontSize="small"
                    sx={{ transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
                  />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          {showDescription && (
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              {t("generative:simplifiedRag.prompt.description")}
            </Typography>
          )}
        </Box>

        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
          <Box>
            <PromptBody
              promptId={promptId}
              setPromptId={setPromptId}
              onTokenCountChange={onTokenCountChange}
            />
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
}

PromptParamsCard.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
