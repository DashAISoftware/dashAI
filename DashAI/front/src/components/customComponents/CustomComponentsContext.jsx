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
  listBaseClasses,
  listCustomComponents,
  updateCustomComponent,
  validateCustomComponent,
} from "../../api/customComponents";

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
  dirty: false,
};

export function CustomComponentsProvider({ children }) {
  const { t } = useTranslation("customComponents");
  const { enqueueSnackbar } = useSnackbar();

  const [components, setComponents] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);

  const [baseClasses, setBaseClasses] = useState([]);
  const [baseInfo, setBaseInfo] = useState(null);
  const [loadingBaseInfo, setLoadingBaseInfo] = useState(false);

  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);

  const refreshList = useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const rows = await listCustomComponents();
      setComponents(rows);
      return rows;
    } catch (err) {
      setListError(err?.message || "Unknown error");
      return [];
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    listBaseClasses()
      .then((rows) => {
        setBaseClasses(rows);
        setDraft((prev) => {
          if (prev.base_class) return prev;
          const defaultBase = rows.find((r) => r.enabled)?.name || "";
          return { ...prev, base_class: defaultBase };
        });
      })
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

  const selectComponent = useCallback((component) => {
    setDraft({
      id: component.id,
      class_name: component.class_name,
      base_class: component.base_class,
      description: component.description || "",
      source_code: component.source_code,
      isNew: false,
      dirty: false,
    });
    setValidation(null);
  }, []);

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
      const result = draft.isNew
        ? await createCustomComponent(payload)
        : await updateCustomComponent(draft.id, payload);
      enqueueSnackbar(
        t(draft.isNew ? "messages.created" : "messages.updated", {
          name: result.class_name,
        }),
        { variant: "success" },
      );
      const rows = await refreshList();
      const saved = rows.find((r) => r.id === result.id);
      if (saved) {
        selectComponent(saved);
      }
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
  }, [canSubmit, draft, enqueueSnackbar, refreshList, selectComponent, t]);

  const remove = useCallback(
    async (component) => {
      try {
        await deleteCustomComponent(component.id);
        enqueueSnackbar(t("messages.deleted", { name: component.class_name }), {
          variant: "success",
        });
        if (draft.id === component.id) {
          startNewDraft();
        }
        await refreshList();
      } catch (err) {
        enqueueSnackbar(err?.message || "Delete failed", { variant: "error" });
      }
    },
    [draft.id, enqueueSnackbar, refreshList, startNewDraft, t],
  );

  const value = useMemo(
    () => ({
      components,
      loadingList,
      listError,
      baseClasses,
      baseInfo,
      loadingBaseInfo,
      draft,
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
      refreshList,
    }),
    [
      components,
      loadingList,
      listError,
      baseClasses,
      baseInfo,
      loadingBaseInfo,
      draft,
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
      refreshList,
    ],
  );

  return (
    <CustomComponentsContext.Provider value={value}>
      {children}
    </CustomComponentsContext.Provider>
  );
}
