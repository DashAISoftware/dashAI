import { useMemo } from "react";
import { Box, Typography, CardContent } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Plot from "react-plotly.js";
import ExportableCard from "../ExportableCard";
import { useTranslation } from "react-i18next";

const CorrelationsTab = ({ correlations }) => {
  const { t } = useTranslation(["datasets"]);
  const theme = useTheme();

  const { columns, zValues, strongCorrelations, leftMargin } = useMemo(() => {
    const cols = Object.keys(correlations);

    // Build symmetric matrix
    const z = cols.map((col1) =>
      cols.map((col2) => {
        if (col1 === col2) return 1;
        return correlations[col1]?.[col2] ?? correlations[col2]?.[col1] ?? 0;
      }),
    );

    // Extract strong correlations (|r| > 0.5, no self-correlations)
    const strong = [];
    cols.forEach((col1, i) => {
      cols.forEach((col2, j) => {
        if (i < j && Math.abs(z[i][j]) > 0.5) {
          strong.push({
            pair: `${col1} - ${col2}`,
            correlation: z[i][j],
          });
        }
      });
    });
    strong.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation));

    const maxLabelLen = Math.max(...cols.map((c) => c.length), 0);
    const leftMargin = Math.min(maxLabelLen * 7 + 20, 300);

    return {
      columns: cols,
      zValues: z,
      strongCorrelations: strong,
      leftMargin,
    };
  }, [correlations]);

  return (
    <ExportableCard filename="correlations" exportData={strongCorrelations}>
      <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
        <Typography variant="h6" fontWeight="bold" mb={6}>
          {t("datasets:label.correlationAnalysis")}
        </Typography>

        <Box mb={8}>
          <Plot
            data={[
              {
                z: zValues,
                x: columns,
                y: columns,
                type: "heatmap",
                colorscale: [
                  [0, "#e57373"],
                  [0.5, theme.palette.background.paper],
                  [1, "#81c784"],
                ],
                zmin: -1,
                zmax: 1,
                text: zValues.map((row) => row.map((val) => val.toFixed(3))),
                texttemplate: "%{text}",
                textfont: {
                  color: theme.palette.text.primary,
                  size: 11,
                },
                hovertemplate: "%{x} — %{y}<br>r = %{z:.3f}<extra></extra>",
                showscale: true,
                colorbar: {
                  title: {
                    text: "r",
                    font: { color: theme.palette.text.primary },
                  },
                  tickfont: { color: theme.palette.text.secondary },
                },
              },
            ]}
            layout={{
              autosize: true,
              height: Math.max(400, columns.length * 40 + 150),
              margin: { l: leftMargin, r: 40, t: 20, b: 120 },
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              xaxis: {
                tickangle: -45,
                tickfont: { color: theme.palette.text.secondary, size: 11 },
                side: "bottom",
              },
              yaxis: {
                tickfont: { color: theme.palette.text.secondary, size: 11 },
                autorange: "reversed",
              },
            }}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%" }}
          />
        </Box>

        <Box>
          <Typography variant="h6" fontWeight="bold" mb={4}>
            {t("datasets:label.strongCorrelations")} (|r| &gt; 0.5)
          </Typography>
          <Box display="flex" flexDirection="column" gap={4}>
            {strongCorrelations.map((d, idx) => (
              <Box
                key={idx}
                display="flex"
                alignItems="center"
                justifyContent="space-between"
                p={4}
                sx={{
                  backgroundColor: theme.palette.ui.panelMedium,
                  borderRadius: 2,
                }}
              >
                <Typography variant="body2" fontWeight={500}>
                  {d.pair}
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  sx={{
                    color: d.correlation > 0 ? "success.main" : "error.main",
                  }}
                >
                  {d.correlation.toFixed(3)}
                </Typography>
              </Box>
            ))}
            {strongCorrelations.length === 0 && (
              <Box p={4}>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  fontStyle="italic"
                >
                  {t("datasets:label.noStrongCorrelationsFound")}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      </CardContent>
    </ExportableCard>
  );
};

export default CorrelationsTab;
