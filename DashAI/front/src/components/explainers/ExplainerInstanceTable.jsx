import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TablePagination,
  TableRow,
} from "@mui/material";

import { getDatasetFile } from "../../api/datasets";
import LeanDatasetTable from "../shared/leanDatasetTable/LeanDatasetTable";

const ROWS_PER_PAGE = 10;

/**
 * Instance picker for a local explainer's explained rows. When the explainer
 * stored its input rows as a dataset (datasetPath), it renders the shared
 * dataset table (feature values, image thumbnails, pagination). Otherwise, for
 * explainers computed before input rows were persisted, it falls back to a
 * simple paginated list of instance labels. Selecting a row calls onSelect
 * with the instance index.
 */
export default function ExplainerInstanceTable({
  datasetPath = null,
  titles,
  selectedIndex,
  onSelect,
}) {
  const [page, setPage] = useState(0);

  if (datasetPath) {
    return (
      <LeanDatasetTable
        fetchPage={(fetchPageIndex, pageSize) =>
          getDatasetFile(datasetPath, fetchPageIndex, pageSize)
        }
        datasetPath={datasetPath}
        initialPageSize={10}
        enableFilters={false}
        enableSearch={false}
        enableColumnVisibility={false}
        enableRowsPerPage={false}
        showExportButton={false}
        selectedRowIndex={selectedIndex}
        onRowClick={(row, globalIndex) => onSelect(globalIndex)}
      />
    );
  }

  const pageStart = page * ROWS_PER_PAGE;
  const pageTitles = titles.slice(pageStart, pageStart + ROWS_PER_PAGE);

  return (
    <div>
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ maxHeight: 520 }}
      >
        <Table size="small" stickyHeader>
          <TableBody>
            {pageTitles.map((title, i) => {
              const globalIndex = pageStart + i;
              return (
                <TableRow
                  key={globalIndex}
                  hover
                  selected={globalIndex === selectedIndex}
                  onClick={() => onSelect(globalIndex)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>{title}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={titles.length}
        page={page}
        onPageChange={(event, newPage) => setPage(newPage)}
        rowsPerPage={ROWS_PER_PAGE}
        rowsPerPageOptions={[ROWS_PER_PAGE]}
      />
    </div>
  );
}

ExplainerInstanceTable.propTypes = {
  datasetPath: PropTypes.string,
  titles: PropTypes.arrayOf(PropTypes.string).isRequired,
  selectedIndex: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
};
