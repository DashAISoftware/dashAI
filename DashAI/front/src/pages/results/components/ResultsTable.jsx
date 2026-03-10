import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { useSnackbar } from "notistack";
import ResultsTableLayout from "./ResultsTableLayout";
import { useNavigate } from "react-router-dom";
import { getComponents } from "../../../api/component";
import PredictionModal from "../../../components/predictions/PredictionModal";
import { useTranslation } from "react-i18next";

// constants
import { extractRows } from "../constants/extractRows";
import { extractColumns } from "../constants/extractColumns";

/**
 * This component renders a table that contains the runs associated to an experiment.
 * @param {string} experimentId id of the experiment whose runs the user wants to analyze.
 */
function ResultsTable({
  runs,
  experiment,
  handleRun,
  handleDeleteRun,
  handleExecuteRuns,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [columnGroupingModel, setColumnGroupingModel] = useState([]);
  const [columnVisibilityModel, setColumnVisibilityModel] = useState({});
  const [loading, setLoading] = useState(false);
  const [showRunResults, setShowRunResults] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [models, setModels] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [predictionModalOpen, setPredictionModalOpen] = useState(false);
  const [selectedRunForPrediction, setSelectedRunForPrediction] =
    useState(null);
  const { t } = useTranslation(["models"]);

  const getModels = async () => {
    return await getComponents({ selectTypes: ["Model"] });
  };

  const handleRunResultsOpen = (run) => {
    setSelectedRun(runs.find((r) => r.id === run.id));
    setShowRunResults(true);
  };

  const handleCloseRunResults = () => {
    setSelectedRun(null);
    setShowRunResults(false);
  };

  const handlePrediction = (run, trainedDatasetId) => {
    setSelectedRunForPrediction(run);
    setPredictionModalOpen(true);
  };

  const handleExplainer = (run) => {
    navigate(`../app/explainers/runs/${run.id}`, {
      state: {
        modelName: run.name,
        taskName: experiment.task_name,
      },
    });
  };

  const processRuns = () => {
    try {
      setLoading(true);

      const extractedRows = extractRows(runs, models);

      const { columns, columnGroupingModel, columnVisibilityModel } =
        extractColumns(
          metrics,
          runs,
          experiment.dataset_id,
          handleRun,
          handleRunResultsOpen,
          handlePrediction,
          handleExplainer,
          handleDeleteRun,
        );

      console.log("Columns:", columns);

      setRows(extractedRows);
      setColumns(columns);
      setColumnGroupingModel(columnGroupingModel);
      setColumnVisibilityModel(columnVisibilityModel);
    } catch (error) {
      enqueueSnackbar(t("models:error.preparingRunsTable"), {
        variant: "error",
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!models || !metrics) return;
    processRuns();
  }, [runs, models, metrics]);

  useEffect(() => {
    if (selectedRun) {
      setSelectedRun(runs.find((r) => r.id === selectedRun.id));
    }
  }, [runs, selectedRun]);

  useEffect(() => {
    const fetchStaticData = async () => {
      const m = await getModels();
      setModels(m);

      const metricComponents = await getComponentsRequest({
        selectTypes: ["Metric"],
        relatedComponent: experiment.task_name,
      });

      setMetrics(
        metricComponents.filter((c) =>
          experiment.test_metrics.includes(c.name),
        ),
      );
    };

    fetchStaticData();
  }, [experiment]);

  return (
    <>
      <ResultsTableLayout
        rows={
          experiment.id
            ? rows.filter(
                (run) => String(run.model_session_id) === String(experiment.id),
              )
            : []
        }
        columns={columns}
        showRunResults={showRunResults}
        loading={loading}
        selectedRun={selectedRun}
        handleCloseRunResults={handleCloseRunResults}
        columnVisibilityModel={columnVisibilityModel}
        columnGroupingModel={columnGroupingModel}
        handleExecuteRuns={handleExecuteRuns}
        handleRun={handleRun}
      />
      <PredictionModal
        isOpen={predictionModalOpen}
        onClose={() => {
          setPredictionModalOpen(false);
          setSelectedRunForPrediction(null);
        }}
        run={selectedRunForPrediction}
      />
    </>
  );
}

ResultsTable.propTypes = {
  runs: PropTypes.array.isRequired,
  experiment: PropTypes.object.isRequired,
};

export default ResultsTable;
