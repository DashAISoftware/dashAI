import { useState, useMemo } from "react";
import {
  Typography,
  Card,
  CardContent,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import GeneratorBody from "../components/GeneratorBody";

export default function GeneratorSection({
  generatorModel,
  setGeneratorModel,
  chunkSize = 0,
  topK = 0,
  promptTokenCount = 0,
  setIsValid,
}) {
  const { t } = useTranslation(["generative"]);
  const [initialModelParams, setInitialModelParams] = useState(null);

  const isAdvanced = useMemo(() => {
    if (!generatorModel?.component || !generatorModel?.params || !initialModelParams) return false;
    return Object.keys(generatorModel.params).some(key => {
      return generatorModel.params[key] !== initialModelParams[key];
    });
  }, [generatorModel?.params, initialModelParams]);

  return (
    <Card sx={{ width: "100%", backgroundColor: "background.paper" }}>
      <CardContent>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          {t("generative:simplifiedRag.generator.description")}
        </Typography>

        <GeneratorBody
          generatorModel={generatorModel}
          setGeneratorModel={setGeneratorModel}
          chunkSize={chunkSize}
          topK={topK}
          promptTokenCount={promptTokenCount}
          setIsValid={setIsValid}
          isAdvanced={isAdvanced}
          setInitialModelParams={setInitialModelParams}
        />
      </CardContent>
    </Card>
  );
}

GeneratorSection.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  chunkSize: PropTypes.number,
  topK: PropTypes.number,
  promptTokenCount: PropTypes.number,
  setIsValid: PropTypes.func.isRequired,
};
