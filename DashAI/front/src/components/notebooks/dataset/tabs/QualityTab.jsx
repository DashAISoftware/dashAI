import React from "react";
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Alert,
} from "@mui/material";
import IssueCard from "../IssueCard";

const QualityTab = ({ qualityInfo, totalRows }) => {
  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {/* Data Quality Summary */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
          <Typography variant="h6" fontWeight="bold" mb={2}>
            Data Quality Summary
          </Typography>

          <Box display="flex" flexWrap="wrap" gap={4}>
            {/* Left Column - Issues Found */}
            <Box flex="1 1 400px" minWidth="300px">
              <Typography
                variant="subtitle1"
                fontWeight={600}
                color="text.secondary"
                mb={2}
              >
                Issues Found
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <IssueCard
                  title="Constant Columns"
                  count={qualityInfo.constant_columns.length}
                  items={qualityInfo.constant_columns}
                  severity="warning"
                />
                <IssueCard
                  title="High Cardinality"
                  count={qualityInfo.high_cardinality_columns.length}
                  items={qualityInfo.high_cardinality_columns}
                  severity="info"
                />
                <IssueCard
                  title="Possible ID Columns"
                  count={qualityInfo.possible_id_columns.length}
                  items={qualityInfo.possible_id_columns}
                  severity="info"
                />
              </Box>
            </Box>

            {/* Right Column - Missing Data Patterns */}
            <Box flex="1 1 400px" minWidth="300px">
              <Typography
                variant="subtitle1"
                fontWeight={600}
                color="text.secondary"
                mb={2}
              >
                Missing Data Patterns
              </Typography>
              {Object.values(qualityInfo.nan_ratio_per_column).every(
                (ratio) => ratio === 0,
              ) ? (
                <Alert severity="success">
                  No missing values detected in the dataset.
                </Alert>
              ) : (
                <Box display="flex" flexDirection="column" gap={2}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      bgcolor: theme.palette.ui.disabled,
                      borderRadius: 2,
                    }}
                  >
                    <Typography variant="h5" fontWeight="bold">
                      {qualityInfo.rows_with_any_nan}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Rows with any missing value
                    </Typography>
                    <Typography variant="caption" color="text.disabled">
                      {(
                        (qualityInfo.rows_with_any_nan / totalRows) *
                        100
                      ).toFixed(1)}
                      % of total
                    </Typography>
                  </Paper>

                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      bgcolor: theme.palette.ui.disabled,
                      borderRadius: 2,
                    }}
                  >
                    <Typography variant="h5" fontWeight="bold">
                      {qualityInfo.rows_with_multiple_nan}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Rows with multiple missing values
                    </Typography>
                    <Typography variant="caption" color="text.disabled">
                      {(
                        (qualityInfo.rows_with_multiple_nan / totalRows) *
                        100
                      ).toFixed(1)}
                      % of total
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Missing Data by Column */}
      <Card>
        <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
          <Typography variant="h6" fontWeight="bold" mb={2}>
            Missing Data by Column
          </Typography>

          <Box display="flex" flexDirection="column" gap={1}>
            {Object.values(qualityInfo.nan_ratio_per_column).every(
              (ratio) => ratio === 0,
            ) ? (
              <Alert severity="success">
                No missing values detected in any column.
              </Alert>
            ) : (
              Object.entries(qualityInfo.nan_ratio_per_column)
                .sort((a, b) => b[1] - a[1])
                .filter(([, ratio]) => ratio > 0)
                .map(([col, ratio]) => (
                  <Box key={col} display="flex" alignItems="center">
                    <Box width={120} sx={{ overflow: "hidden" }}>
                      <Typography
                        variant="body2"
                        fontWeight={500}
                        color="text.primary"
                        noWrap
                        title={col}
                      >
                        {col}
                      </Typography>
                    </Box>

                    <Box flex={1} mx={2}>
                      <Box
                        sx={{
                          height: 12,
                          borderRadius: 6,
                          backgroundColor: "grey.300",
                          overflow: "hidden",
                        }}
                      >
                        <Box
                          sx={{
                            height: "100%",
                            width: `${ratio * 100}%`,
                            backgroundColor:
                              ratio > 0.2
                                ? "error.main"
                                : ratio > 0.05
                                  ? "warning.main"
                                  : "success.main",
                          }}
                        />
                      </Box>
                    </Box>

                    <Box width={60} textAlign="right">
                      <Typography variant="body2" color="text.secondary">
                        {(ratio * 100).toFixed(2)}%
                      </Typography>
                    </Box>
                  </Box>
                ))
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default QualityTab;
2;
