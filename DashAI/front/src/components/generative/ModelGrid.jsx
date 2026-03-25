import { Box, Grid, Pagination } from "@mui/material";
import ModelCard from "./ModelCard";

export const MODEL_COLORS = [
  "#1976d2",
  "#7b1fa2",
  "#2e7d32",
  "#e65100",
  "#0288d1",
  "#c62828",
];

export const MODELS_PER_PAGE = 4;

export default function ModelGrid({
  models,
  selectedModelName,
  page,
  onSelect,
  onPageChange,
}) {
  const pageModels = models.slice(
    (page - 1) * MODELS_PER_PAGE,
    page * MODELS_PER_PAGE,
  );

  return (
    <>
      <Grid container spacing={2} data-tour="model-selection">
        {pageModels.map((model, indexOnPage) => {
          const globalIndex = (page - 1) * MODELS_PER_PAGE + indexOnPage;
          const color =
            model.color ?? MODEL_COLORS[globalIndex % MODEL_COLORS.length];
          return (
            <Grid
              size={{ xl: 6, lg: 6, md: 6, sm: 12, xs: 12 }}
              key={model.name}
            >
              <ModelCard
                model={model}
                color={color}
                isSelected={selectedModelName === model.name}
                onClick={() => onSelect(model, globalIndex)}
              />
            </Grid>
          );
        })}
      </Grid>

      {models.length > MODELS_PER_PAGE && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
          <Pagination
            count={Math.ceil(models.length / MODELS_PER_PAGE)}
            page={page}
            onChange={(_, value) => onPageChange(value)}
            color="primary"
            size="small"
          />
        </Box>
      )}
    </>
  );
}
