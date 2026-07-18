import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * A labelled section wrapper for the info bar.
 * @param {object} props
 * @param {string} props.title - Section heading.
 * @param {JSX.Element} props.children - Section content.
 * @returns {JSX.Element}
 */
function Section({ title, children }) {
  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

/**
 * Right-side info panel explaining how the RAG feature works,
 * listing settings documentation and usage tips.
 * @returns {JSX.Element}
 */
export default function RAGInfoBar() {
  const { t } = useTranslation(["generative"]);

  return (
    <Box display="flex" flexDirection="column" gap={2}>
      <Box>
        <Typography variant="subtitle1">
          {t("generative:rag.rightPanel.title")}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {t("generative:rag.rightPanel.subtitle")}
        </Typography>
      </Box>

      <Section title={t("generative:rag.rightPanel.howItWorksTitle")}>
        <Box component="ul" sx={{ pl: 2, my: 0 }}>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.howItWorks.step1")}
          </Typography>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.howItWorks.step2")}
          </Typography>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.howItWorks.step3")}
          </Typography>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.howItWorks.step4")}
          </Typography>
        </Box>
      </Section>

      <Section title={t("generative:rag.rightPanel.settingsTitle")}>
        <Box display="flex" flexDirection="column" gap={2}>
          <Box>
            <Typography variant="body2">
              {t("generative:rag.rightPanel.settings.documents.title")}
            </Typography>
            <Box component="ul" sx={{ pl: 2, my: 0 }}>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.documents.point1",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.documents.point2",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.documents.point3",
                )}
              </Typography>
            </Box>
          </Box>

          <Box>
            <Typography variant="body2">
              {t("generative:rag.rightPanel.settings.chunking.title")}
            </Typography>
            <Box component="ul" sx={{ pl: 2, my: 0 }}>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.chunking.point1",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.chunking.point2",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.chunking.point3",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.chunking.point4",
                )}
              </Typography>
            </Box>
          </Box>

          <Box>
            <Typography variant="body2">
              {t(
                "generative:rag.rightPanel.settings.retriever.title",
              )}
            </Typography>
            <Box component="ul" sx={{ pl: 2, my: 0 }}>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.retriever.point1",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.retriever.point2",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.retriever.point3",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.retriever.point4",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.retriever.point5",
                )}
              </Typography>
            </Box>
          </Box>

          <Box>
            <Typography variant="body2">
              {t("generative:rag.rightPanel.settings.llm.title")}
            </Typography>
            <Box component="ul" sx={{ pl: 2, my: 0 }}>
              <Typography component="li" variant="body2" color="textSecondary">
                {t("generative:rag.rightPanel.settings.llm.point1")}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t("generative:rag.rightPanel.settings.llm.point2")}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t("generative:rag.rightPanel.settings.llm.point3")}
              </Typography>
            </Box>
          </Box>

          <Box>
            <Typography variant="body2">
              {t("generative:rag.rightPanel.settings.prompt.title")}
            </Typography>
            <Box component="ul" sx={{ pl: 2, my: 0 }}>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.prompt.point1",
                )}
              </Typography>
              <Typography component="li" variant="body2" color="textSecondary">
                {t(
                  "generative:rag.rightPanel.settings.prompt.point2",
                )}
              </Typography>
            </Box>
          </Box>
        </Box>
      </Section>

      <Section title={t("generative:rag.rightPanel.tipsTitle")}>
        <Box component="ul" sx={{ pl: 2, my: 0 }}>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.tips.tip1")}
          </Typography>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.tips.tip2")}
          </Typography>
          <Typography component="li" variant="body2" color="textSecondary">
            {t("generative:rag.rightPanel.tips.tip3")}
          </Typography>
        </Box>
      </Section>
    </Box>
  );
}
