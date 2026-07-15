import React, { useState } from "react";
import PropTypes from "prop-types";
import { Box, TablePagination } from "@mui/material";
import { useTheme } from "@mui/material/styles";

import { getDatasetFile } from "../../api/datasets";
import LeanDatasetTable from "../shared/leanDatasetTable/LeanDatasetTable";
import "../shared/leanDatasetTable/leanDatasetTable.css";

const ROWS_PER_PAGE = 10;

/**
 * Instance picker for a local explainer's explained rows. When the explainer
 * stored its input rows as a dataset (datasetPath), it renders the shared
 * dataset table (feature values, image thumbnails, pagination). Otherwise, for
 * explainers computed before input rows were persisted, it falls back to a
 * list of instance labels styled like the dataset table. Selecting a row calls
 * onSelect with the instance index.
 */
export default function ExplainerInstanceTable({
  datasetPath = null,
  titles,
  selectedIndex,
  onSelect,
}) {
  const theme = useTheme();
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
    <Box
      className="lean-root"
      sx={{
        "--lean-header-bg": theme.palette.ui.panelDark,
        "--lean-header-fg": theme.palette.text.primary,
        "--lean-body-bg": theme.palette.ui.panelDark,
        "--lean-row-hover": theme.palette.action.hover,
      }}
    >
      <div className="lean-scroll">
        <table className="lean-table">
          <tbody>
            {pageTitles.map((title, i) => {
              const globalIndex = pageStart + i;
              const isSelected = globalIndex === selectedIndex;
              return (
                <tr
                  key={globalIndex}
                  className="lean-row lean-row--clickable"
                  onClick={() => onSelect(globalIndex)}
                  style={{
                    backgroundColor: isSelected
                      ? theme.palette.action.selected
                      : undefined,
                  }}
                >
                  <td className="lean-cell" title={title}>
                    {title}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <TablePagination
        component="div"
        sx={{
          backgroundColor: "var(--lean-body-bg)",
          border: "1px solid rgba(128, 128, 128, 0.3)",
          borderTop: "none",
          borderBottomLeftRadius: 4,
          borderBottomRightRadius: 4,
        }}
        count={titles.length}
        page={page}
        rowsPerPage={ROWS_PER_PAGE}
        showFirstButton
        showLastButton
        onPageChange={(_event, newPage) => setPage(newPage)}
        rowsPerPageOptions={[ROWS_PER_PAGE]}
        labelRowsPerPage=""
        slotProps={{ select: { sx: { display: "none" } } }}
      />
    </Box>
  );
}

ExplainerInstanceTable.propTypes = {
  datasetPath: PropTypes.string,
  titles: PropTypes.arrayOf(PropTypes.string).isRequired,
  selectedIndex: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
};
