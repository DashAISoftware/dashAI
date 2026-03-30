import { Grid, Paper, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import EditOptimizerDialog from "./EditOptimizerDialog";
import OptimizationTableSelectOptimizer from "./OptimizationTableSelectOptimizer";
import { checkIfHaveOptimazers } from "../../utils/schema";
import { getComponents } from "../../api/component";
import { useTranslation } from "react-i18next";

/**
 * This component renders a table to display the models that are currently in the experiment
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 */
function OptimizationTable({ newExp, setNewExp }) {
  const [selectedOptimizer, setSelectedOptimizer] = useState({});
  const [models, setModels] = useState([]);
  const { t } = useTranslation(["experiments", "common"]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getComponents({ selectTypes: ["Model"] });
        setModels(response);
      } catch (error) {
        console.error("Error fetching models:", error);
      }
    };
    fetchModels();
  }, []);

  const handleUpdateParameters = (id) => (newValues) => {
    setNewExp((prevExp) => {
      return {
        ...prevExp,
        runs: prevExp.runs.map((run) => {
          if (run.id === id) {
            return {
              ...run,
              optimizer_name: newExp.runs.find((r) => r.id === id)
                .optimizer_name,
              optimizer_parameters: newValues,
            };
          }
          return run;
        }),
      };
    });
  };

  const handleAddOptimizer = async (name, defaultValues, id) => {
    // sets the default values of the newly added optimizer, making optional the parameter configuration

    const optimizerRun = newExp.runs.map((run) => {
      if (run.id === id) {
        return {
          ...run,
          optimizer_name: name,
          optimizer_parameters: defaultValues,
        };
      }
      return run;
    });

    setNewExp((prevExp) => {
      return {
        ...prevExp,
        runs: optimizerRun,
      };
    });
  };

  const handleSelectedOptimizer = async (name, defaultValues, id) => {
    setSelectedOptimizer((prevSelectedOptimizer) => {
      return {
        ...prevSelectedOptimizer,
        [id]: name,
      };
    });

    handleAddOptimizer(name, defaultValues, id);
  };

  const columns = React.useMemo(() => [
    {
      field: "name",
      headerName: t("common:name"),
      minWidth: 300,
      editable: false,
    },
    {
      field: "model",
      headerName: t("common:model"),
      minWidth: 300,
      editable: false,
      valueGetter: (value) => {
        const model = models.find((model) => model.name === value);
        return model && model.display_name ? model.display_name : value;
      },
    },
    {
      field: "optimizer",
      headerName: t("experiments:label.configureOptimizer"),
      minWidth: 300,
      renderCell: (params) => (
        <OptimizationTableSelectOptimizer
          taskName={newExp.task_name}
          optimizerName={params.row.optimizer_name}
          handleSelectedOptimizer={(optimizerName, defaultValues) =>
            handleSelectedOptimizer(optimizerName, defaultValues, params.row.id)
          }
        />
      ),
    },
    {
      field: "actions",
      headerName: t("common:actions"),
      type: "actions",
      minWidth: 100,
      getActions: (params) => {
        if (!params.row.optimizer_name) {
          return [];
        }

        return [
          <EditOptimizerDialog
            key="edit-component"
            optimizerToConfigure={params.row.optimizer_name}
            updateParameters={handleUpdateParameters(params.row.id)}
            paramsInitialValues={params.row.optimizer_parameters}
          />,
        ];
      },
    },
  ]);

  return (
    <Paper sx={{ py: 1, px: 2 }}>
      {/* Title */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="subtitle1" component="h3">
          {t("experiments:label.modelsInExperiment")}
        </Typography>
      </Grid>

      {/* Models Table */}
      <DataGrid
        rows={newExp.runs.filter(checkIfHaveOptimazers)}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        }}
        pageSizeOptions={[5]}
        disableRowSelectionOnClick
        density="compact"
        autoHeight
        hideFooterSelectedRowCount
      />
    </Paper>
  );
}

OptimizationTable.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    step: PropTypes.string,
    created: PropTypes.instanceOf(Date),
    last_modified: PropTypes.instanceOf(Date),
    runs: PropTypes.array,
  }),
  setNewExp: PropTypes.func.isRequired,
};

export default OptimizationTable;
