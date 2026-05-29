import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Grid,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { useTheme } from "@mui/material/styles";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";

import { useTourContext } from "../tour/TourProvider";
import { getDatasets as getDatasetsRequest } from "../../api/datasets";
import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";
import { useTableLocalization } from "../../../utils/useTableLocalization";

function SelectDatasetStep({ newExp, setNewExp, setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [requestError, setRequestError] = useState(false);
  const tourContext = useTourContext();
  const { t } = useTranslation(["experiments", "common"]);
  const theme = useTheme();
  const localization = useTableLocalization();

  const columns = useMemo(
    () => [
      {
        accessorKey: "name",
        header: t("common:name"),
      },
      {
        accessorKey: "created",
        header: t("common:createdAt"),
        Cell: ({ cell }) => formatDate(cell.getValue()),
      },
      {
        accessorKey: "last_modified",
        header: t("common:lastModified"),
        Cell: ({ cell }) => formatDate(cell.getValue()),
      },
    ],
    [t],
  );

  useEffect(() => {
    setNewExp({ ...newExp, input_columns: [], output_columns: [] });
  }, []);

  const getDatasets = async () => {
    setLoading(true);
    try {
      const datasets = await getDatasetsRequest();
      setDatasets(datasets);
    } catch (error) {
      enqueueSnackbar(t("experiments:error.errorFetchingDatasets"), {
        variant: "error",
      });
      setRequestError(true);

      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };
  // fetch datasets when the component is mounting
  useEffect(() => {
    getDatasets();
  }, []);

  // autoselect dataset and enable next button if some dataset was selected previously.
  useEffect(() => {
    if (typeof newExp.dataset === "object" && newExp.dataset !== null) {
      const found = datasets.find(
        (dataset) => newExp.dataset.id === dataset.id,
      );
      if (found) {
        setNextEnabled(true);
      }
    }
  }, [datasets]);

  const handleRowClick = (row) => {
    const dataset = row.original;
    setNewExp({ ...newExp, dataset });
    setNextEnabled(true);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
  };

  const datasetsTable = useMaterialReactTable({
    columns,
    data: datasets,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    enableRowSelection: false,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => handleRowClick(row),
      sx: { cursor: "pointer" },
    }),
    state: { isLoading: loading },
    enableGlobalFilter: false,
    enableColumnFilters: false,
    enableSorting: true,
    enablePagination: true,
    muiPaginationProps: { rowsPerPageOptions: [10, 25] },
    initialState: { pagination: { pageSize: 10, pageIndex: 0 } },
    localization,
  });

  return (
    <React.Fragment>
      {/* Title and new datasets button */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 8 }}
      >
        <Typography variant="subtitle1" component="h3">
          {t("experiments:label.selectDatasetTitle")}
        </Typography>
      </Grid>

      {/* Datasets Table */}

      {datasets.length === 0 && !loading && !requestError && (
        <React.Fragment>
          <Alert severity="warning" sx={{ mb: 4 }}>
            <AlertTitle>
              {t("experiments:label.noDatasetsAvailable")}
            </AlertTitle>
            <Trans i18nKey="experiments:label.noDatasetsAvailableGoToDataTab">
              Go to
              <Link component={RouterLink} to="/app/data?action=upload">
                data tab
              </Link>
              to upload one first.
            </Trans>
          </Alert>
          <Typography></Typography>
        </React.Fragment>
      )}
      <Paper data-tour="exp-dataset-selector">
        <MaterialReactTable table={datasetsTable} />
      </Paper>
    </React.Fragment>
  );
}

SelectDatasetStep.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    input_columns: PropTypes.arrayOf(PropTypes.string),
    output_columns: PropTypes.arrayOf(PropTypes.string),
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
  setNextEnabled: PropTypes.func.isRequired,
};
export default SelectDatasetStep;
