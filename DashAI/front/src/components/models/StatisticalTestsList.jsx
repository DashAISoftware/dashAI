import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  TextField,
  CircularProgress,
  Button,
  Stack,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Search as SearchIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import { getComponents } from "../../api/component";
import StatisticalTestItem from "./StatisticalTestItem";

export default function StatisticalTestsList({
  runs,
  session,
  onTestSelect,
  loading: initialLoading = false,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models"]);
  const { enqueueSnackbar } = useSnackbar();

  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(initialLoading);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTest, setSelectedTest] = useState(null);

  // Filtrar runs que hayan terminado exitosamente
  const finishedRuns = useMemo(
    () => runs.filter((run) => run.status === 3),
    [runs],
  );

  // Traer tests estadísticos del backend
  useEffect(() => {
    const fetchTests = async () => {
      try {
        setLoading(true);
        const response = await getComponents({
          selectTypes: ["StatisticalTest"],
        });
        setTests(response.filter((comp) => comp.metadata?.posthoc === false));
      } catch (error) {
        console.error("Error fetching statistical tests:", error);
        enqueueSnackbar(t("models:error.fetchingStatisticalTests"), {
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    if (finishedRuns.length >= 2) {
      fetchTests();
    }
  }, [finishedRuns.length, enqueueSnackbar, t]);

  // Clasificar tests por tipo (paramétricos vs no-paramétricos)
  const { parametricTests, nonParametricTests } = useMemo(() => {
    const parametric = [];
    const nonParametric = [];

    tests.forEach((test) => {
      const isParametric = test.metadata?.is_parametric === true;
      if (isParametric) {
        parametric.push(test);
      } else {
        nonParametric.push(test);
      }
    });

    return { parametricTests: parametric, nonParametricTests: nonParametric };
  }, [tests]);

  // Filtrar tests por búsqueda
  const filteredParametricTests = useMemo(() => {
    if (!searchQuery.trim()) return parametricTests;
    const query = searchQuery.toLowerCase();
    return parametricTests.filter((test) =>
      test.metadata?.name.toLowerCase().includes(query),
    );
  }, [searchQuery, parametricTests]);

  const filteredNonParametricTests = useMemo(() => {
    if (!searchQuery.trim()) return nonParametricTests;
    const query = searchQuery.toLowerCase();
    return nonParametricTests.filter((test) =>
      test.metadata?.name.toLowerCase().includes(query),
    );
  }, [searchQuery, nonParametricTests]);

  const handleTestSelect = (test) => {
    setSelectedTest(test);
  };

  const handleRunTest = () => {
    if (selectedTest && finishedRuns.length >= 2) {
      onTestSelect(selectedTest, finishedRuns);
    }
  };

  // Mostrar mensaje si no hay suficientes runs
  if (finishedRuns.length < 2) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
        }}
      >
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
            {t("models:label.minTwoRunsRequired")}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        height: "100%",
        width: "100%",
      }}
    >
      {/* Content */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          p: 2,
        }}
      >
        {/* Search Box */}
        <TextField
          fullWidth
          size="small"
          placeholder={t("models:label.searchTests")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <SearchIcon sx={{ mr: 1, color: "text.secondary" }} />
              ),
            },
          }}
          sx={{ mb: 2, flexShrink: 0 }}
        />

        {loading ? (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              flex: 1,
            }}
          >
            <CircularProgress size={32} />
          </Box>
        ) : (
          <>
            {/* Parametric Tests */}
            {filteredParametricTests.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 700,
                    color: "primary.main",
                    mb: 1,
                    textTransform: "uppercase",
                    fontSize: "0.75rem",
                    letterSpacing: 0.5,
                  }}
                >
                  {t("models:label.parametricTests")}
                </Typography>
                <Box
                  sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}
                >
                  {filteredParametricTests.map((test) => (
                    <StatisticalTestItem
                      key={test.name}
                      test={test}
                      isSelected={selectedTest?.name === test.name}
                      onSelect={handleTestSelect}
                      numberOfRuns={finishedRuns.length}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* Non-Parametric Tests */}
            {filteredNonParametricTests.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 700,
                    color: "secondary.main",
                    mb: 1,
                    textTransform: "uppercase",
                    fontSize: "0.75rem",
                    letterSpacing: 0.5,
                  }}
                >
                  {t("models:label.nonParametricTests")}
                </Typography>
                <Box
                  sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}
                >
                  {filteredNonParametricTests.map((test) => (
                    <StatisticalTestItem
                      key={test.name}
                      test={test}
                      isSelected={selectedTest?.name === test.name}
                      onSelect={handleTestSelect}
                      numberOfRuns={finishedRuns.length}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* No results message */}
            {filteredParametricTests.length === 0 &&
              filteredNonParametricTests.length === 0 && (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    flex: 1,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: "text.secondary", textAlign: "center" }}
                  >
                    {t("models:label.noTestsMatch")}
                  </Typography>
                </Box>
              )}
          </>
        )}
      </Box>

      {/* Footer with action button */}
      {selectedTest && finishedRuns.length >= 2 && (
        <Box
          sx={{
            p: 2,
            borderTop: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            backgroundColor: theme.palette.action.hover,
          }}
        >
          <Stack direction="column" gap={1}>
            <Typography variant="caption" color="text.secondary">
              {finishedRuns.length} {t("models:label.runsSelected")}
            </Typography>
            <Button
              variant="contained"
              fullWidth
              onClick={handleRunTest}
              disabled={loading}
            >
              {t("models:label.configureTest")}
            </Button>
          </Stack>
        </Box>
      )}
    </Box>
  );
}

StatisticalTestsList.propTypes = {
  runs: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      status: PropTypes.number.isRequired,
    }),
  ).isRequired,
  session: PropTypes.object,
  onTestSelect: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};
