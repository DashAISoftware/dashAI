import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from "@mui/material";

import { getDatasetFile } from "../../api/datasets";

const ROWS_PER_PAGE = 8;

const isImageValue = (value) =>
  typeof value === "string" && value.startsWith("data:image");

/**
 * Paginated table of the rows a local explainer explained, used to pick an
 * instance. Rows come from the stored input DashAIDataset via the existing
 * dataset file endpoint (images arrive as data URIs). When no dataset path is
 * available it falls back to a list of instance titles. Clicking a row calls
 * onSelect with the row's global index (its instance index).
 */
export default function ExplainerInstanceTable({
  datasetPath = null,
  titles = [],
  selectedIndex,
  onSelect,
}) {
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [total, setTotal] = useState(titles.length);
  const [page, setPage] = useState(0);

  useEffect(() => {
    if (!datasetPath) {
      setTotal(titles.length);
      return undefined;
    }
    let cancelled = false;
    getDatasetFile(datasetPath, page, ROWS_PER_PAGE)
      .then((response) => {
        if (cancelled) return;
        const fetchedRows = response?.rows ?? [];
        setRows(fetchedRows);
        setTotal(response?.total ?? fetchedRows.length);
        setColumns(fetchedRows.length ? Object.keys(fetchedRows[0]) : []);
      })
      .catch((error) => {
        if (!cancelled) console.error(error);
      });
    return () => {
      cancelled = true;
    };
  }, [datasetPath, page, titles.length]);

  const pageStart = page * ROWS_PER_PAGE;
  const fallbackTitles = titles.slice(pageStart, pageStart + ROWS_PER_PAGE);

  return (
    <Box>
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ maxHeight: 520 }}
      >
        <Table size="small" stickyHeader>
          {datasetPath && columns.length > 0 && (
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell key={column} sx={{ fontWeight: 600 }}>
                    {column}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
          )}
          <TableBody>
            {datasetPath
              ? rows.map((row, i) => {
                  const globalIndex = pageStart + i;
                  return (
                    <TableRow
                      key={globalIndex}
                      hover
                      selected={globalIndex === selectedIndex}
                      onClick={() => onSelect(globalIndex)}
                      sx={{ cursor: "pointer" }}
                    >
                      {columns.map((column) => (
                        <TableCell key={column}>
                          {isImageValue(row[column]) ? (
                            <Box
                              component="img"
                              src={row[column]}
                              alt=""
                              sx={{
                                height: 44,
                                width: 44,
                                objectFit: "cover",
                                borderRadius: 0.5,
                                display: "block",
                              }}
                            />
                          ) : (
                            String(row[column] ?? "-")
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })
              : fallbackTitles.map((title, i) => {
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
        count={total}
        page={page}
        onPageChange={(event, newPage) => setPage(newPage)}
        rowsPerPage={ROWS_PER_PAGE}
        rowsPerPageOptions={[ROWS_PER_PAGE]}
      />
    </Box>
  );
}

ExplainerInstanceTable.propTypes = {
  datasetPath: PropTypes.string,
  titles: PropTypes.arrayOf(PropTypes.string),
  selectedIndex: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
};
