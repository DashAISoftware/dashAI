import { useMemo } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import ComponentTreeBuilder from "../../../../components/shared/componentTree/ComponentTreeBuilder";
import FormSchemaWithPrompts from "../../../../components/generative/RAG/FormSchemaWithPrompts";
import { resolveLocalizedText } from "../../../../utils/localize";
import { resolveRetrieverRepresentation } from "../../../../components/generative/RAG/retrieverRepresentation";
import { resolveRetrieverSchemaSummary } from "../../../../components/generative/RAG/schemaSummary";
import { isCompositeTreeComplete } from "../../../../components/generative/RAG/compositeTreeValidity";
import { RETRIEVER_PARENT } from "../../../../components/generative/RAG/retrieverParents";
import { resolveRetrieverDefaults } from "./resolveRetrieverDefaults";

/**
 * Tree builder for composite retrievers (Sequential, Parallel, MMR Reranker,
 * agentic ones). It is the generic component tree configured for retrievers:
 * the registry parent, the form that edits a retriever (with its prompts), the
 * retriever defaults, the captions, and the texts.
 *
 * @param {object} props
 * @param {string} props.rootComponent - Name of the root composite retriever.
 * @param {object} [props.rootParams] - Initial params of the root, including its
 *   children.
 * @param {string} [props.rootParent] - Registry parent whose components the
 *   root may be, so a field restricted to chunk scorers never offers a plain
 *   retriever as root. Defaults to every retriever.
 * @param {function} props.onChange - Receives the serialised tree on every change.
 * @param {function(boolean): void} [props.onValidityChange] - Receives whether
 *   every composite in the tree has its children, on load and on every change.
 *   Loading reports validity only: it never calls `onChange`.
 *   The parent uses it to keep its Done/Next action disabled while a composite
 *   is empty.
 * @returns {JSX.Element} The retriever tree builder.
 */
export default function CompositeRetrieverBuilder({
  rootComponent,
  rootParams,
  rootParent = RETRIEVER_PARENT,
  onChange,
  onValidityChange,
}) {
  const { t } = useTranslation(["generative"]);

  /**
   * Reports whether every composite in a serialised tree is complete.
   * @param {object} tree - The serialised `{component, params}` tree.
   * @param {object} context - Carries `findComponent`.
   */
  const reportValidity = (tree, context) => {
    onValidityChange?.(isCompositeTreeComplete(tree, context.findComponent));
  };

  /**
   * Reports an edited tree and whether it is complete.
   * @param {object} tree - The serialised `{component, params}` tree.
   * @param {object} context - Carries `findComponent`.
   */
  const handleTreeChange = (tree, context) => {
    onChange(tree, context);
    reportValidity(tree, context);
  };

  const labels = useMemo(
    () => ({
      loading: t("generative:rag.common.loading"),
      configureNode: t("generative:rag.composite.configureNode"),
      addChild: t("generative:rag.composite.addChild"),
      removeNode: t("generative:rag.composite.removeNode"),
      selectComponent: t("generative:rag.composite.selectModel"),
      parameters: t("generative:rag.composite.parameters"),
      containerNote: t("generative:rag.composite.nestedCompositeNote"),
    }),
    [t],
  );

  /**
   * Caption of a node: its schema summary, else its representation, else its
   * description.
   * @param {object} context - The node, its component info and the lookups.
   * @returns {string|null} The caption.
   */
  const renderCaption = ({ node, info, findComponent, i18n }) => {
    const translateLabel = (label) =>
      t(`rag.schemaSummary.labels.${label}`, { defaultValue: label });
    return (
      resolveRetrieverSchemaSummary(
        info,
        node.params,
        findComponent,
        translateLabel,
      ) ||
      resolveRetrieverRepresentation(info, node.params, i18n) ||
      resolveLocalizedText(info?.description, i18n)
    );
  };

  return (
    <ComponentTreeBuilder
      rootComponent={rootComponent}
      rootParams={rootParams}
      onChange={handleTreeChange}
      onLoad={reportValidity}
      parent={rootParent}
      resolveDefaults={resolveRetrieverDefaults}
      FormComponent={FormSchemaWithPrompts}
      renderCaption={renderCaption}
      labels={labels}
    />
  );
}

CompositeRetrieverBuilder.propTypes = {
  rootComponent: PropTypes.string.isRequired,
  rootParams: PropTypes.object,
  rootParent: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onValidityChange: PropTypes.func,
};
