import { useEffect, useMemo, useState } from "react";
import {
    Box,
    Button,
    Divider,
    Typography,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    CircularProgress,
} from "@mui/material";

import ChatIcon from "@mui/icons-material/Chat";
import Footer from "../threeSectionLayout/Footer";
import CollapsibleListAgent from "../threeSectionLayout/CollapsibleListAgent";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useTranslation } from "react-i18next";
import { useAgent } from "./contexts/AgentContext";
import { useSnackbar } from "notistack";
import { generateSequentialName } from "../../utils/nameGenerator";
import AgentConfigField from "./AgentConfigField";
import {
    fetchDefaultAgentParameters,
    createAgentConfiguration,
    fetchAgentConfigurations,
    updateAgentConfiguration,
    deleteAgentConfiguration,
    fetchAgentConfigurationById,
} from "../../api/agent";


const NEW_CONFIGURATION_ID = -1;

export default function AgentRightBar() {
    const { t } = useTranslation(["agent", "common"]);
    const { enqueueSnackbar } = useSnackbar();

    const { selectedConfigurationId, setSelectedConfigurationId } = useAgent();
    const [editingConfigurationId, setEditingConfigurationId] = useState(null);
    const [searchConfigurationQuery, setSearchConfigurationQuery] = useState("");

    const [configurations, setConfigurations] = useState([]);

    const [loadingList, setLoadingList] = useState(false);
    const [loadingStepTwo, setLoadingStepTwo] = useState(false);
    const [showBackConfirm, setShowBackConfirm] = useState(false);

    const [availableModels, setAvailableModels] = useState([]);
    const [availableFamilies, setAvailableFamilies] = useState([]);
    const [selectedModel, setSelectedModel] = useState(null);

    const [formState, setFormState] = useState({
        configurationName: "",
        configurationDescription: "",
        familyModelName: "",
        parameters: {},
    });
    const [persistedSnapshot, setPersistedSnapshot] = useState(null);

    const isNewConfiguration = editingConfigurationId === NEW_CONFIGURATION_ID;

    const normalizeToolsField = (fieldSchema) => {
        if (!fieldSchema || fieldSchema.type !== "array") return fieldSchema;
        const options = fieldSchema.toolsName || fieldSchema.items?.enum || [];
        const displayNames = fieldSchema.display_tools_name || [];

        return {
            ...fieldSchema,
            items: {
                ...(fieldSchema.items || { type: "string" }),
                enum: Array.isArray(options) ? options : [],
            },
            optionLabels: Array.isArray(displayNames) ? displayNames : [],
        };
    };

    const normalizeModelSchema = (rawModel) => {
        const rawProperties = rawModel?.schema?.properties || {};
        const normalizedProperties = Object.keys(rawProperties).reduce((acc, key) => {
            if (key === "selected_tools") {
                acc[key] = normalizeToolsField(rawProperties[key]);
                return acc;
            }
            acc[key] = rawProperties[key];
            return acc;
        }, {});

        return {
            ...rawModel,
            schema: {
                ...(rawModel?.schema || {}),
                properties: normalizedProperties,
            },
        };
    };

    const getDefaultValueFromSchema = (fieldSchema) => {
        if (fieldSchema.placeholder !== undefined) {
            return fieldSchema.placeholder;
        }

        if (fieldSchema.type === "array") return [];
        if (fieldSchema.type === "integer" || fieldSchema.type === "number") return "";
        if (fieldSchema.type === "boolean") return false;
        return "";
    };

    const buildInitialParamsFromSchema = (schemaProperties) => {
        return Object.keys(schemaProperties).reduce((acc, key) => {
            acc[key] = getDefaultValueFromSchema(schemaProperties[key]);
            return acc;
        }, {});
    };

    const getAllToolsFromModel = (model) => {
        const toolsEnum = model.schema.properties.selected_tools?.items?.enum;
        return Array.isArray(toolsEnum) ? toolsEnum : [];
    };
    const getModelFamily = (model) => {
        return model.metadata?.family_model || "Unknown";
    };

    const getModelFamilyLabel = (family) => {
        if (family === "Unknown") return t("agent:label.unknownFamily");
        return family;
    };

    const buildSavePayload = (form, model) => ({
        configuration_name: form.configurationName,
        configuration_description: form.configurationDescription,
        family_model_name: form.familyModelName,
        model_name: model.name,
        parameters: form.parameters,
        tools: form.parameters.selected_tools,
    });

    const areFormsEqual = (a, b) => {
        return JSON.stringify(a) === JSON.stringify(b);
    };

    const filteredConfigurations = useMemo(() => {
        if (!searchConfigurationQuery.trim()) return configurations;
        const lowerQuery = searchConfigurationQuery.toLowerCase();
        return configurations.filter((configuration) =>
            (configuration.name || "").toLowerCase().includes(lowerQuery),
        );
    }, [configurations, searchConfigurationQuery]);

    const hasUnsavedChanges = useMemo(() => {
        if (!persistedSnapshot) return false;
        if (selectedModel?.name !== persistedSnapshot.modelName) return true;
        return !areFormsEqual(formState, persistedSnapshot.form);
    }, [formState, persistedSnapshot, selectedModel]);

    const loadConfigurations = async () => {
        setLoadingList(true);
        try {
            const data = await fetchAgentConfigurations();
            setConfigurations(data);
        } catch (error) {
            enqueueSnackbar(t("agent:error.failedToLoadConfigurations"), {
                variant: "error",
            });
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => {
        loadConfigurations();
    }, []);

    const updateParameterValue = (key, value) => {
        setFormState((previous) => ({
            ...previous,
            parameters: {
                ...previous.parameters,
                [key]: value,
            },
        }));
    };

    const hydrateStepFromModel = (model, options) => {
        const baseParams = buildInitialParamsFromSchema(model.schema.properties);
        const mergedParams = {
            ...baseParams,
            ...options.parameters,
        };

        const nextForm = {
            configurationName: options.configurationName,
            configurationDescription: options.configurationDescription,
            familyModelName: options.familyModelName,
            parameters: {
                ...mergedParams,
                selected_tools: options.tools,
            },
        };

        setSelectedModel(model);
        setFormState(nextForm);
        setPersistedSnapshot({ form: nextForm, modelName: model.name });
    };

    const loadDefaultModelsForCreate = async () => {
        setLoadingStepTwo(true);
        try {
            const models = await fetchDefaultAgentParameters();
            const normalizedModels = models.map((model) => normalizeModelSchema(model));

            setAvailableModels(normalizedModels);
            const families = Array.from(
                new Set(normalizedModels.map((model) => getModelFamily(model))),
            );
            setAvailableFamilies(families);
            if (!normalizedModels.length) {
                enqueueSnackbar(t("agent:error.noAvailableModels"), { variant: "warning" });
                return;
            }

            const { defaultName } = generateSequentialName({
                base: "Agent_Configuration",
                items: configurations,
                getName: (configuration) => configuration.name,
            });

            const firstModel = normalizedModels[0];
            hydrateStepFromModel(firstModel, {
                configurationName: defaultName,
                configurationDescription: "",
                familyModelName: getModelFamily(firstModel),
                tools: getAllToolsFromModel(firstModel),
            });
        } catch (error) {
            enqueueSnackbar(t("agent:error.failedToLoadDefaultParameters"), {
                variant: "error",
            });
        } finally {
            setLoadingStepTwo(false);
        }
    };

    const loadConfigurationForEdit = async (configurationId) => {
        setLoadingStepTwo(true);
        try {
            const [models, configuration] = await Promise.all([
                fetchDefaultAgentParameters(),
                fetchAgentConfigurationById(configurationId),
            ]);

            const normalizedModels = models.map((model) => normalizeModelSchema(model));
            setAvailableModels(normalizedModels);
            const families = Array.from(
                new Set(normalizedModels.map((model) => getModelFamily(model))),
            );
            setAvailableFamilies(families);

            const matchingModel = normalizedModels.find(
                (model) => model.name === configuration.model_name,
            );

            if (!matchingModel) {
                enqueueSnackbar(t("agent:error.configurationModelNotFound"), {
                    variant: "error",
                });
                return;
            }

            hydrateStepFromModel(matchingModel, {
                configurationName: configuration.configuration_name,
                configurationDescription: configuration.configuration_description || "",
                familyModelName: configuration.family_model_name || getModelFamily(matchingModel),
                parameters: configuration.parameters,
                tools: configuration.tools,
            });
        } catch (error) {
            enqueueSnackbar(t("agent:error.failedToLoadConfigurationDetail"), {
                variant: "error",
            });
        } finally {
            setLoadingStepTwo(false);
        }
    };

    const handleCreateConfiguration = async () => {
        setEditingConfigurationId(NEW_CONFIGURATION_ID);
        await loadDefaultModelsForCreate();
    };

    const handleSelectConfigurationById = (configurationId) => {
        setSelectedConfigurationId(configurationId);
    };

    const handleDeleteConfigurationById = async (configurationId) => {
        try {
            await deleteAgentConfiguration(configurationId);
            setConfigurations((previousConfigurations) =>
                previousConfigurations.filter(
                    (configuration) => configuration.id !== configurationId,
                ),
            );

            if (selectedConfigurationId === configurationId) {
                setSelectedConfigurationId(null);
            }
            if (editingConfigurationId === configurationId) {
                setEditingConfigurationId(null);
            }

            enqueueSnackbar(t("agent:message.deleteConfigurationSuccess"), {
                variant: "success",
            });
        } catch (error) {
            enqueueSnackbar(t("agent:error.failedToDeleteConfiguration"), {
                variant: "error",
            });
        }
    };

    const handleEditConfiguration = async (configurationId) => {
        setSelectedConfigurationId(configurationId);
        setEditingConfigurationId(configurationId);
        await loadConfigurationForEdit(configurationId);
    };

    const handleFamilyChange = (familyName) => {
        const familyModels = availableModels.filter(
            (model) => getModelFamily(model) === familyName,
        );
        const nextModel = familyModels[0];

        setSelectedModel(nextModel);
        setFormState((previous) => ({
            ...previous,
            familyModelName: familyName,
            parameters: {
                ...buildInitialParamsFromSchema(nextModel.schema.properties),
                selected_tools: isNewConfiguration ? getAllToolsFromModel(nextModel) : [],
            },
        }));
    };

    const handleModelChange = (modelName) => {
        const model = availableModels.find((item) => item.name === modelName);
        const schemaDefaults = buildInitialParamsFromSchema(model.schema.properties);

        setSelectedModel(model);
        setFormState((previous) => ({
            ...previous,
            familyModelName: getModelFamily(model),
            parameters: {
                ...schemaDefaults,
                selected_tools: isNewConfiguration
                    ? getAllToolsFromModel(model)
                    : schemaDefaults.selected_tools || [],
            },
        }));
    };

    const goBackToList = () => {
        setEditingConfigurationId(null);
        setSelectedModel(null);
        setAvailableModels([]);
        setAvailableFamilies([]);
        setPersistedSnapshot(null);
        setFormState({
            configurationName: "",
            configurationDescription: "",
            familyModelName: "",
            parameters: {},
        });
    };

    const handleBackToConfigurationStep = () => {
        if (hasUnsavedChanges) {
            setShowBackConfirm(true);
            return;
        }
        goBackToList();
    };

    const handleSaveConfiguration = async () => {
        if (!formState.configurationName.trim()) {
            enqueueSnackbar(t("agent:error.configurationNameRequired"), {
                variant: "warning",
            });
            return;
        }

        const payload = buildSavePayload(formState, selectedModel);

        try {
            if (isNewConfiguration) {
                const createdConfiguration = await createAgentConfiguration(payload);
                setSelectedConfigurationId(createdConfiguration.id);
                enqueueSnackbar(t("agent:message.configurationSaved"), {
                    variant: "success",
                });
            } else {
                await updateAgentConfiguration(editingConfigurationId, payload);
                setSelectedConfigurationId(editingConfigurationId);
                enqueueSnackbar(t("agent:message.configurationUpdated"), {
                    variant: "success",
                });
            }

            await loadConfigurations();
            setPersistedSnapshot({ form: formState, modelName: selectedModel.name });
            goBackToList();
        } catch (error) {
            enqueueSnackbar(t("agent:error.failedToSaveConfiguration"), {
                variant: "error",
            });
        }
    };

    const getConfigurationDeleteConfirmationContent = (configuration) =>
        t("agent:label.confirmDeleteConversation", {
            name: configuration.name,
        });

    const selectedModelProperties = selectedModel ? selectedModel.schema.properties : {};

    return (
        <SideBar>
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    overflow: "hidden",
                    height: "100%",
                    width: "100%",
                }}
            >
                <Divider sx={{ width: "100%", bgcolor: "divider" }} />

                {!editingConfigurationId ? (
                    <>
                        <Box
                            p={2}
                            sx={{
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "flex-start",
                                gap: 1,
                            }}
                        >
                            <NewItemButton
                                onClick={handleCreateConfiguration}
                                title={t("agent:button.newConfiguration")}
                            />
                            <Typography variant="body1" color="textSecondary">
                                {t("agent:label.availableConfigurations")}
                            </Typography>
                        </Box>

                        <Box px={2} pb={2} flex="0 0 auto">
                            <SearchBar
                                placeholder={t("agent:label.searchConfigurations")}
                                value={searchConfigurationQuery}
                                onChange={(event) => setSearchConfigurationQuery(event.target.value)}
                            />
                        </Box>

                        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

                        <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
                            <CollapsibleListAgent
                                items={filteredConfigurations}
                                selectedItemId={selectedConfigurationId}
                                onItemClick={handleSelectConfigurationById}
                                onItemDelete={handleDeleteConfigurationById}
                                onItemEdit={handleEditConfiguration}
                                title={t("agent:label.configurations")}
                                Icon={ChatIcon}
                                defaultOpen={true}
                                getDeleteConfirmationContent={getConfigurationDeleteConfirmationContent}
                            />
                        </Box>

                        {loadingList && (
                            <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                                <CircularProgress size={20} />
                            </Box>
                        )}
                    </>
                ) : (
                    <Box
                        sx={{
                            flex: 1,
                            display: "flex",
                            flexDirection: "column",
                            overflow: "hidden",
                        }}
                    >
                        <Box
                            sx={{
                                p: 2,
                                flexShrink: 0,
                                display: "flex",
                                flexDirection: "column",
                                gap: 0.5,
                            }}
                        >
                            <Button
                                variant="text"
                                size="small"
                                onClick={handleBackToConfigurationStep}
                                sx={{ alignSelf: "flex-start", pl: 0, mb: 0.5 }}
                            >
                                ← {t("common:back")}
                            </Button>
                            <Typography variant="h6" color="text.primary">
                                {t("agent:label.configurationTitle")}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {formState.configurationName ||
                                    configurations.find((c) => c.id === editingConfigurationId)?.name ||
                                    ""}
                            </Typography>
                        </Box>

                        <Divider sx={{ width: "100%", bgcolor: "divider" }} />

                        {loadingStepTwo ? (
                            <Box
                                sx={{
                                    flex: 1,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                }}
                            >
                                <CircularProgress size={26} />
                            </Box>
                        ) : (
                            <Box
                                sx={{
                                    flex: 1,
                                    overflowY: "auto",
                                    p: 2,
                                }}
                            >
                                <TextField
                                    fullWidth
                                    size="small"
                                    label={t("agent:label.configurationName")}
                                    value={formState.configurationName}
                                    onChange={(event) =>
                                        setFormState((previous) => ({
                                            ...previous,
                                            configurationName: event.target.value,
                                        }))
                                    }
                                    sx={{ mb: 2 }}
                                />

                                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                                    <InputLabel>{t("agent:label.familyModel")}</InputLabel>
                                    <Select
                                        value={formState.familyModelName}
                                        label={t("agent:label.familyModel")}
                                        onChange={(event) => handleFamilyChange(event.target.value)}
                                    >
                                        {availableFamilies.map((family) => (
                                            <MenuItem key={family} value={family}>
                                                {getModelFamilyLabel(family)}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>

                                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                                    <InputLabel>{t("agent:label.modelName")}</InputLabel>
                                    <Select
                                        value={selectedModel?.name || ""}
                                        label={t("agent:label.modelName")}
                                        onChange={(event) => handleModelChange(event.target.value)}
                                    >
                                        {availableModels
                                            .filter((model) => getModelFamily(model) === formState.familyModelName)
                                            .map((model) => (
                                                <MenuItem key={model.name} value={model.name}>
                                                    {model.display_name || model.name}
                                                </MenuItem>
                                            ))}
                                    </Select>
                                </FormControl>

                                <Divider sx={{ my: 2 }} />

                                {Object.keys(selectedModelProperties).map((fieldKey) => (
                                    <AgentConfigField
                                        key={fieldKey}
                                        fieldKey={fieldKey}
                                        fieldSchema={selectedModelProperties[fieldKey]}
                                        value={formState.parameters[fieldKey]}
                                        onChange={updateParameterValue}
                                    />
                                ))}

                                <Box
                                    sx={{
                                        display: "flex",
                                        justifyContent: "flex-end",
                                        pt: 1,
                                        pb: 1,
                                    }}
                                >
                                    <Button variant="contained" onClick={handleSaveConfiguration}>
                                        {t("agent:button.saveConfiguration")}
                                    </Button>
                                </Box>
                            </Box>
                        )}
                    </Box>
                )}

                <Footer />
            </Box>

            <Dialog open={showBackConfirm} onClose={() => setShowBackConfirm(false)}>
                <DialogTitle>{t("agent:label.unsavedChangesTitle")}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{t("agent:label.unsavedChangesMessage")}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowBackConfirm(false)}>{t("common:cancel")}</Button>
                    <Button
                        color="warning"
                        onClick={() => {
                            setShowBackConfirm(false);
                            goBackToList();
                        }}
                    >
                        {t("common:back")}
                    </Button>
                </DialogActions>
            </Dialog>
        </SideBar>
    );
}