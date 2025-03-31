import React, { useState } from "react";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import { Grid, Paper, Typography } from "@mui/material";
import DeleteItemModal from "../custom//DeleteItemModal";
import EditModelDialog from "./EditModelDialog";
import ModelsTableSelectMetric from "./ModelsTableSelectMetric";

/**
 * This component renders a table to display the models that are currently in the experiment
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 */
function ModelsTable({ newExp, setNewExp }) {
  const [selectedMetric, setSelectedMetric] = useState({});

  const handleDeleteModel = (id) => {
    setNewExp({
      ...newExp,
      runs: newExp.runs.filter((model) => model.id !== id),
    });
  };
  const handleUpdateParameters = (id) => (newValues) => {
    setNewExp((prevExp) => {
      return {
        ...prevExp,
        runs: prevExp.runs.map((model) => {
          if (model.id === id) {
            return {
              ...model,
              params: newValues,
              goal_metric: selectedMetric[id],
            };
          }
          return model;
        }),
      };
    });
  };

  const handleAddMetric = async (name, id) => {
    // sets the default values of the newly added optimizer, making optional the parameter configuration

    const metricRun = newExp.runs.map((run) => {
      if (run.id === id) {
        return {
          ...run,
          goal_metric: name,
        };
      }
      return run;
    });

    setNewExp((prevExp) => {
      return {
        ...prevExp,
        runs: metricRun,
      };
    });
  };

  const handleSelectedMetric = async (name, id) => {
    setSelectedMetric((prevSelectedMetric) => {
      return {
        ...prevSelectedMetric,
        [id]: name,
      };
    });

    handleAddMetric(name, id);
  };

  const columns = React.useMemo(
    () => [
      {
        field: "name",
        headerName: "Name",
        flex: 1, // This makes the column take available space proportionally
        editable: false,
      },
      {
        field: "model",
        headerName: "Model",
        flex: 1, // Ensures it resizes properly
        editable: false,
      },
      {
        field: "actions",
        type: "actions",
        flex: 0.5, // Less space needed since it's just buttons
        getActions: (params) => [
          <EditModelDialog
            key="edit-component"
            modelToConfigure={params.row.model}
            updateParameters={handleUpdateParameters(params.id)}
            paramsInitialValues={params.row.params}
          />,
          <DeleteItemModal
            key="delete-component"
            deleteFromTable={() => handleDeleteModel(params.id)}
          />,
        ],
      },
      {
        field: "metric",
        headerName: "Optimization Metric (Optional)",
        flex: 1, // Since it's a dropdown, give it more space
        renderCell: (params) => (
          <ModelsTableSelectMetric
            taskName={newExp.task_name}
            metricName={selectedMetric[params.row.id]}
            handleSelectedMetric={(metricName) =>
              handleSelectedMetric(metricName, params.row.id)
            }
          />
        ),
      },
    ],
    [handleDeleteModel],
  );

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
          Current models in the experiment
        </Typography>
      </Grid>

      {/* Models Table */}
      <DataGrid
        rows={newExp.runs}
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

ModelsTable.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    input_columns: PropTypes.arrayOf(PropTypes.number),
    output_columns: PropTypes.arrayOf(PropTypes.number),
    splits: PropTypes.shape({
      training: PropTypes.number,
      validation: PropTypes.number,
      testing: PropTypes.number,
    }),
    step: PropTypes.string,
    created: PropTypes.instanceOf(Date),
    last_modified: PropTypes.instanceOf(Date),
    runs: PropTypes.array,
  }),
  setNewExp: PropTypes.func.isRequired,
};

export default ModelsTable;
