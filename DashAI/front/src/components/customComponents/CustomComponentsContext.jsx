import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  createCustomComponent,
  deleteCustomComponent,
  getBaseClassInfo,
  getComponentSource,
  listBaseClasses,
  listCustomComponents,
  updateCustomComponent,
  validateCustomComponent,
} from "../../api/customComponents";
import { getComponents } from "../../api/component";

const CLASS_NAME_REGEX = /^[A-Z][A-Za-z0-9_]*$/;

const CustomComponentsContext = createContext(null);

export function useCustomComponents() {
  const ctx = useContext(CustomComponentsContext);
  if (!ctx) {
    throw new Error(
      "useCustomComponents must be used within CustomComponentsProvider",
    );
  }
  return ctx;
}

const EMPTY_DRAFT = {
  id: null,
  class_name: "",
  base_class: "",
  description: "",
  source_code: "",
  isNew: true,
  isOverride: false,
  origin: "custom",
  dirty: false,
};

function originOf(customRow) {
  if (customRow) return customRow.is_override ? "custom-override" : "custom";
  return "core";
}

export function CustomComponentsProvider({ children }) {
  const { t } = useTranslation("customComponents");
  const { enqueueSnackbar } = useSnackbar();

  const [registry, setRegistry] = useState([]);
  const [customRows, setCustomRows] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);

  const [baseClasses, setBaseClasses] = useState([]);
  const [baseInfo, setBaseInfo] = useState(null);
  const [loadingBaseInfo, setLoadingBaseInfo] = useState(false);

  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);

  const refreshList = useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const [regRows, customList] = await Promise.all([
        getComponents(),
        listCustomComponents(),
      ]);
      setRegistry(regRows);
      setCustomRows(customList);
      return { registry: regRows, custom: customList };
    } catch (err) {
      setListError(err?.message || "Unknown error");
      return { registry: [], custom: [] };
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    listBaseClasses()
      .then(setBaseClasses)
      .catch(() => setBaseClasses([]));
  }, []);

  useEffect(() => {
    if (!draft.base_class) {
      setBaseInfo(null);
      return;
    }
    setLoadingBaseInfo(true);
    let cancelled = false;
    getBaseClassInfo(draft.base_class)
      .then((info) => {
        if (cancelled) return;
        setBaseInfo(info);
        setDraft((prev) => {
          if (prev.isNew && !prev.dirty && !prev.source_code) {
            return { ...prev, source_code: info.skeleton };
          }
          return prev;
        });
      })
      .catch(() => !cancelled && setBaseInfo(null))
      .finally(() => !cancelled && setLoadingBaseInfo(false));
    return () => {
      cancelled = true;
    };
  }, [draft.base_class]);

  const setDraftField = useCallback((patch) => {
    setDraft((prev) => ({ ...prev, ...patch, dirty: true }));
    setValidation(null);
  }, []);

  const startNewDraft = useCallback(() => {
    const defaultBase = baseClasses.find((r) => r.enabled)?.name || "";
    setDraft({
      ...EMPTY_DRAFT,
      base_class: defaultBase,
    });
    setValidation(null);
  }, [baseClasses]);

  const _customRowByName = useCallback(
    (name) => customRows.find((r) => r.class_name === name),
    [customRows],
  );

  const selectComponent = useCallback(
    async (registryItem) => {
      const customRow = _customRowByName(registryItem.name);
      setValidation(null);
      setLoadingDraft(true);
      try {
        if (customRow) {
          setDraft({
            id: customRow.id,
            class_name: customRow.class_name,
            base_class: customRow.base_class,
            description: customRow.description || "",
            source_code: customRow.source_code,
            isNew: false,
            isOverride: customRow.is_override,
            origin: customRow.is_override ? "custom-override" : "custom",
            dirty: false,
          });
        } else {
          const info = await getComponentSource(registryItem.name);
          setDraft({
            id: null,
            class_name: info.class_name,
            base_class: info.base_class,
            description: "",
            source_code: info.source_code,
            isNew: true,
            isOverride: true,
            origin: info.origin,
            dirty: false,
          });
        }
      } catch (err) {
        enqueueSnackbar(err?.message || "Failed to load component source", {
          variant: "error",
        });
      } finally {
        setLoadingDraft(false);
      }
    },
    [_customRowByName, enqueueSnackbar],
  );

  const classNameValid = useMemo(
    () => CLASS_NAME_REGEX.test(draft.class_name),
    [draft.class_name],
  );

  const canSubmit = useMemo(
    () =>
      classNameValid &&
      !!draft.base_class &&
      draft.source_code.trim().length > 0,
    [classNameValid, draft.base_class, draft.source_code],
  );

  const runValidate = useCallback(async () => {
    if (!canSubmit) return;
    setValidating(true);
    try {
      const res = await validateCustomComponent({
        source_code: draft.source_code,
        class_name: draft.class_name,
        base_class: draft.base_class,
      });
      setValidation(res);
    } catch (err) {
      setValidation({
        ok: false,
        errors: [err?.message || "Validation request failed"],
        warnings: [],
      });
    } finally {
      setValidating(false);
    }
  }, [canSubmit, draft]);

  const save = useCallback(async () => {
    if (!canSubmit) return;
    setSaving(true);
    try {
      const payload = {
        class_name: draft.class_name,
        base_class: draft.base_class,
        source_code: draft.source_code,
        description: draft.description,
      };
      const result =
        draft.id != null
          ? await updateCustomComponent(draft.id, payload)
          : await createCustomComponent(payload);

      enqueueSnackbar(
        t(draft.id == null ? "messages.created" : "messages.updated", {
          name: result.class_name,
        }),
        { variant: "success" },
      );
      await refreshList();
      setDraft({
        id: result.id,
        class_name: result.class_name,
        base_class: result.base_class,
        description: result.description || "",
        source_code: result.source_code,
        isNew: false,
        isOverride: result.is_override,
        origin: result.is_override ? "custom-override" : "custom",
        dirty: false,
      });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.errors) {
        setValidation({
          ok: false,
          errors: detail.errors,
          warnings: detail.warnings || [],
        });
      } else {
        enqueueSnackbar(
          typeof detail === "string" ? detail : err?.message || "Save failed",
          { variant: "error" },
        );
      }
    } finally {
      setSaving(false);
    }
  }, [canSubmit, draft, enqueueSnackbar, refreshList, t]);

  const remove = useCallback(
    async (customRow, { isRevert = false } = {}) => {
      try {
        await deleteCustomComponent(customRow.id);
        enqueueSnackbar(
          t(isRevert ? "messages.reverted" : "messages.deleted", {
            name: customRow.class_name,
          }),
          { variant: "success" },
        );
        if (draft.id === customRow.id) {
          startNewDraft();
        }
        await refreshList();
      } catch (err) {
        enqueueSnackbar(err?.message || "Delete failed", { variant: "error" });
      }
    },
    [draft.id, enqueueSnackbar, refreshList, startNewDraft, t],
  );

  const revert = useCallback(async () => {
    if (draft.id == null || !draft.isOverride) return;
    const row = customRows.find((r) => r.id === draft.id);
    if (!row) return;
    await remove(row, { isRevert: true });
  }, [customRows, draft.id, draft.isOverride, remove]);

  const mergedItems = useMemo(() => {
    const customByName = new Map(customRows.map((r) => [r.class_name, r]));
    const items = registry.map((item) => {
      const row = customByName.get(item.name);
      return {
        ...item,
        customRow: row || null,
        origin: originOf(row),
        base_type: item.type,
      };
    });
    for (const row of customRows) {
      if (!items.some((i) => i.name === row.class_name)) {
        items.push({
          name: row.class_name,
          type: row.base_type,
          base_type: row.base_type,
          customRow: row,
          origin: row.is_override ? "custom-override" : "custom",
          orphan: true,
        });
      }
    }
    return items;
  }, [registry, customRows]);

  const value = useMemo(
    () => ({
      items: mergedItems,
      registry,
      customRows,
      loadingList,
      listError,
      baseClasses,
      baseInfo,
      loadingBaseInfo,
      draft,
      loadingDraft,
      validation,
      validating,
      saving,
      classNameValid,
      canSubmit,
      setDraftField,
      startNewDraft,
      selectComponent,
      runValidate,
      save,
      remove,
      revert,
      refreshList,
    }),
    [
      mergedItems,
      registry,
      customRows,
      loadingList,
      listError,
      baseClasses,
      baseInfo,
      loadingBaseInfo,
      draft,
      loadingDraft,
      validation,
      validating,
      saving,
      classNameValid,
      canSubmit,
      setDraftField,
      startNewDraft,
      selectComponent,
      runValidate,
      save,
      remove,
      revert,
      refreshList,
    ],
  );

  return (
    <CustomComponentsContext.Provider value={value}>
      {children}
    </CustomComponentsContext.Provider>
  );
}
