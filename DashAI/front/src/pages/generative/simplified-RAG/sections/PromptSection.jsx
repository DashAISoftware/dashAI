import {
  Typography,
  Card,
  CardContent,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import PromptBody from "../components/PromptBody";

export default function PromptSection({
  promptId,
  setPromptId,
  onTokenCountChange,
}) {
  const { t } = useTranslation(["generative"]);

  return (
    <Card sx={{ backgroundColor: "background.paper" }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          {t("generative:simplifiedRag.prompt.description")}
        </Typography>

        <PromptBody
          promptId={promptId}
          setPromptId={setPromptId}
          onTokenCountChange={onTokenCountChange}
        />
      </CardContent>
    </Card>
  );
}

PromptSection.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
