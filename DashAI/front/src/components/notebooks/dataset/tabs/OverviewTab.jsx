import React, { useState } from "react";
import { Box, Typography, Card, CardContent, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
} from "recharts";
import DatasetTable from "../DatasetTable";
import ExportableCard from "../ExportableCard";
import { useTranslation } from "react-i18next";
import { getColorByColumnType } from "../../../../utils";

const OverviewTab = ({
  dataset,
  dtypes,
  columnTypes,
  nan,
  total_rows,
  fetchDatasetPage,
  onEditColumnName,
}) => {
  const { t } = useTranslation(["datasets", "common"]);

  const theme = useTheme();
  const [activeBarIndex, setActiveBarIndex] = useState(null);
  const missingData = Object.entries(nan).map(([col, count]) => ({
    column: col,
    missing: count,
    percentage: ((count / total_rows) * 100).toFixed(1),
  }));

  // Get all unique dtype values
  const dtypeValues = new Set(Object.values(dtypes ?? {}));

  // Count occurrences of each dtype
  const typeCounts = Array.from(dtypeValues).map((dtype) => [
    dtype,
    Object.values(dtypes).filter((v) => v === dtype).length,
  ]);

  return (
    <Box display="flex" flexDirection="column" gap={8}>
      {/* Data View */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              justifyContent: "space-between",
              mb: 2,
            }}
          >
            <Typography variant="h6">
              {t("datasets:label.datasetPreview")}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              {typeCounts.map(([type, count]) => (
                <Chip
                  key={type}
                  label={`${count} ${type}`}
                  size="small"
                  sx={{
                    backgroundColor: getColorByColumnType(type, theme),
                    color: "#fff",
                    fontWeight: 600,
                    fontSize: "0.75rem",
                    height: "22px",
                  }}
                />
              ))}
            </Box>
          </Box>
          <DatasetTable
            fetchPage={fetchDatasetPage}
            deps={[dataset.file_path]}
            initialPageSize={10}
            datasetPath={dataset.file_path}
            datasetId={dataset.id}
            onEditColumn={onEditColumnName}
            editableColumns={true}
            columnTypes={
              columnTypes && Object.keys(columnTypes).length > 0
                ? columnTypes
                : dtypes
            }
          />
        </CardContent>
      </Card>
      {/* Missing Values Overview — only shown when there are missing values */}
      {missingData.some((data) => data.missing > 0) && (
        <ExportableCard
          filename="missing_values_overview"
          exportData={missingData}
          data-section="missing-values-overview"
        >
          <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 2,
              }}
            >
              <Typography variant="h6">
                {t("datasets:label.missingValuesOverview")}
              </Typography>
              <Chip
                label={`Total: ${Object.values(nan).reduce(
                  (sum, v) => sum + v,
                  0,
                )}`}
                size="small"
                variant="outlined"
                sx={{ fontWeight: "bold" }}
              />
            </Box>
            <Box sx={{ width: "100%", height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={missingData} margin={{ bottom: 120 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="column"
                    angle={-45}
                    textAnchor="end"
                    interval={0}
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                  />
                  <YAxis />
                  <Tooltip
                    cursor={false}
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      borderRadius: 4,
                      color: theme.palette.text.primary,
                      border: `1px solid ${theme.palette.divider}`,
                    }}
                    labelStyle={{ color: theme.palette.text.primary }}
                  />
                  <Bar
                    dataKey="missing"
                    fill="#8884d8"
                    name={t("common:missing")}
                    activeBar={false}
                    onMouseEnter={(_, index) => setActiveBarIndex(index)}
                    onMouseLeave={() => setActiveBarIndex(null)}
                  >
                    {missingData.map((_, index) => (
                      <Cell
                        key={index}
                        fill="#8884d8"
                        fillOpacity={
                          index === activeBarIndex
                            ? 1
                            : activeBarIndex !== null
                              ? 0.5
                              : 0.7
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </ExportableCard>
      )}
    </Box>
  );
};

export default OverviewTab;
