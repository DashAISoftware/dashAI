import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  Autocomplete,
  TextField,
  Typography,
  Box,
  Divider,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import FormSchema from "../../../../components/shared/FormSchema";
import FormSchemaContainer from "../../../../components/shared/FormSchemaContainer";
import { resolveDefaults } from "../../../../utils/schema";

const COMPOSITE_TYPES = ["SequentialRetriever", "ParallelRetriever"];

export default function RetrieverNodeConfig({
  open,
  nodeId,
  nodeData,
  allComponents,
  leafRegistry,
  onSave,
  onClose,
}) {
  const { t } = useTranslation(["generative"]);

  const allOptions = useMemo(() => {
    const list = [...allComponents];
    for (const key of Object.keys(leafRegistry)) {
      list.push(...(leafRegistry[key] || []));
    }
    return list.filter((c) => c.configurable_object !== false);
  }, [allComponents, leafRegistry]);

  const [selectedModel, setSelectedModel] = useState(null);
  const [params, setParams] = useState({});
  const [initialParams, setInitialParams] = useState({});

  useEffect(() => {
    if (!nodeData || !allOptions.length) return;
    const found = allOptions.find((c) => c.name === nodeData.component);
    setSelectedModel(found || null);
    const p = nodeData.params || {};
    setParams(p);
    setInitialParams(p);
  }, [nodeData, allOptions]);

  const isComposite = selectedModel && COMPOSITE_TYPES.includes(selectedModel.name);

  const getDisplay = (opt) => {
    if (!opt) return "";
    const dn = opt.display_name;
    if (!dn) return opt.name || "";
    if (typeof dn === "string") return dn;
    return dn.en || dn.es || String(dn);
  };

  const handleModelChange = async (_e, newVal) => {
    setSelectedModel(newVal);
    if (newVal) {
      const defaults = await resolveDefaults(newVal.name);
      setParams(defaults);
      setInitialParams(defaults);
    } else {
      setParams({});
    }
  };

  const handleSave = () => {
    if (!selectedModel) return;
    onSave(nodeId, selectedModel.name, params);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle
        sx={{
          bgcolor: "background.paper",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {t("generative:simplifiedRag.composite.configureNode")}
        <IconButton onClick={onClose} size="small" sx={{ color: "text.secondary" }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Autocomplete
            options={allOptions}
            value={selectedModel}
            onChange={handleModelChange}
            getOptionLabel={(opt) => getDisplay(opt)}
            isOptionEqualToValue={(a, b) => a.name === b.name}
            groupBy={(opt) => {
              if (COMPOSITE_TYPES.includes(opt.name)) return t("generative:simplifiedRag.composite.compositeGroup");
              return t("generative:simplifiedRag.composite.simpleGroup");
            }}
            renderInput={(p) => (
              <TextField {...p} label={t("generative:simplifiedRag.composite.selectModel")} />
            )}
          />

          {isComposite && (
            <Typography variant="caption" color="text.secondary">
              {t("generative:simplifiedRag.composite.nestedCompositeNote")}
            </Typography>
          )}

          {selectedModel && (
            <>
              <Divider />
              <Typography variant="subtitle2">
                {t("generative:simplifiedRag.composite.parameters")}
              </Typography>
              <FormSchemaContainer key={`node-config-${nodeId}-${selectedModel.name}`}>
                <FormSchema
                  model={selectedModel.name}
                  initialValues={initialParams}
                  autoSave
                  onFormSubmit={(values) => setParams(values)}
                  hideButtons
                  excludeFields={isComposite ? ["children"] : []}
                />
              </FormSchemaContainer>
            </>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
        <Button onClick={onClose} variant="outlined">
          {t("common:cancel")}
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={!selectedModel}>
          {t("common:save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

RetrieverNodeConfig.propTypes = {
  open: PropTypes.bool.isRequired,
  nodeId: PropTypes.string.isRequired,
  nodeData: PropTypes.object,
  allComponents: PropTypes.array.isRequired,
  leafRegistry: PropTypes.object.isRequired,
  onSave: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
};
