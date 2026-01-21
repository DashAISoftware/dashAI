import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Paper,
  Alert,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
} from "recharts";
import DatasetTable from "../DatasetTable";
import { useTranslation } from "react-i18next";

const OverviewTab = ({
  dataset,
  dtypes,
  nan,
  total_rows,
  fetchDatasetPage,
}) => {
  const { t } = useTranslation(["datasets", "common"]);

  const theme = useTheme();
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
    <Box display="flex" flexDirection="column" gap={4}>
      {/* Data View */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
          <Typography variant="h6" gutterBottom>
            {t("datasets:label.datasetPreview")}
          </Typography>
          <DatasetTable
            fetchPage={fetchDatasetPage}
            deps={[dataset.file_path]}
            initialPageSize={10}
            datasetPath={dataset.file_path}
          />
        </CardContent>
      </Card>
      {/* Missing Values Overview */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
          <Typography variant="h6" gutterBottom>
            {t("datasets:label.missingValuesOverview")}
          </Typography>
          {missingData.some((data) => data.missing > 0) ? (
            <Box sx={{ width: "100%", height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={missingData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="column" />
                  <YAxis />
                  <Tooltip
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
                    fill="rgba(136, 132, 216, 0.7)"
                    name={t("common:missing")}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Alert severity="success">
              {t("datasets:label.noMissingValues")}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Column Types Distribution */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
          <Typography variant="h6" gutterBottom>
            {t("datasets:label.columnTypesDistribution")}
          </Typography>
          <Grid container spacing={2}>
            {typeCounts.map(([type, count]) => (
              <Grid
                item
                xs={12}
                sm={6}
                md={4}
                key={type}
                sx={{ width: "150px" }}
              >
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    textAlign: "center",
                    bgcolor: theme.palette.ui.disabled,
                    borderRadius: 2,
                  }}
                >
                  <Typography variant="h4" fontWeight="bold">
                    {count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {type}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default OverviewTab;
