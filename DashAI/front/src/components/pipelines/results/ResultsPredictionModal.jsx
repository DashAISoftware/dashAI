import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  Card,
  CardContent,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { getPipelinePredictionSummary } from "../../../api/pipeline";

function PredictionSummary({ predictName }) {
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [summary, setSummary] = useState({});
  const { enqueueSnackbar } = useSnackbar();

  const handleTabChange = (_, newValue) => {
    setTab(newValue);
  };

  const getPredictSummary = async () => {
    setLoading(true);
    try {
      const res = await getPipelinePredictionSummary(predictName);
      setSummary(res);
      if (res.data_type === "string") {
        setTab(2);
      }
    } catch (error) {
      enqueueSnackbar("Error when trying to get the prediction summary");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getPredictSummary();
  }, [predictName]);

  if (loading) {
    return <CircularProgress size={24} />;
  }

  return (
    <Box my={2}>
      <Paper sx={{ width: "100%" }}>
        <Tabs value={tab} onChange={handleTabChange} variant="scrollable">
          <Tab label="Info" />
          <Tab label="Summary" disabled={summary.data_type === "string"} />
          <Tab label="Sample" />
        </Tabs>
        <Box sx={{ p: 3 }}>
          {tab === 0 && (
            <Box>
              <Typography variant="subtitle1">Name</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {predictName ?? "-"}
              </Typography>
            </Box>
          )}
          {tab === 1 && summary.data_type === "regression" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Regression Statistics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Mean
                      </Typography>
                      <Typography variant="h5">
                        {summary.statistics?.mean?.toFixed(2) ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Median
                      </Typography>
                      <Typography variant="h5">
                        {summary.statistics?.median?.toFixed(2) ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Std Deviation
                      </Typography>
                      <Typography variant="h5">
                        {summary.statistics?.std?.toFixed(2) ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Minimum
                      </Typography>
                      <Typography variant="h5">
                        {summary.statistics?.min?.toFixed(2) ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Maximum
                      </Typography>
                      <Typography variant="h5">
                        {summary.statistics?.max?.toFixed(2) ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Total Predictions
                      </Typography>
                      <Typography variant="h5">
                        {summary.total_data_points ?? "-"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          )}
          {tab === 1 && summary.data_type === "classification" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Class Distribution
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Class</TableCell>
                      <TableCell align="right">Occurrences</TableCell>
                      <TableCell align="right">Percentage</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {summary.class_distribution?.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.Class}</TableCell>
                        <TableCell align="right">{row.Ocurrences}</TableCell>
                        <TableCell align="right">{row.Percentage}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
          {tab === 2 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Sample Predictions (First 50)
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Index</TableCell>
                      <TableCell align="right">Predicted Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {summary.sample_data?.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.id}</TableCell>
                        <TableCell align="right">
                          {typeof row.value === "number"
                            ? row.value.toFixed(2)
                            : row.value}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </Box>
      </Paper>
    </Box>
  );
}

export default PredictionSummary;
