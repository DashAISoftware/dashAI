from abc import abstractmethod
from typing import Dict, List, Type

from DashAI.back.insights.base import BaseInsightAnalyzer
from DashAI.back.insights.context import AnalysisContext


class BaseExplainerInsightAnalyzer(BaseInsightAnalyzer):
    """Shared system prompt for every explainer-consumer analyzer.

    The system message is identical across every explainer analyzer below;
    subclasses only implement ``_user_message(facts)`` to describe their
    own facts shape.
    """

    def build_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        facts = context.data
        language = (context.metadata or {}).get("language", "en")
        return [
            {
                "role": "system",
                "content": (
                    "You are an assistant that explains machine learning "
                    "explainability results to data scientists. Be concise "
                    f"and answer in {language}."
                ),
            },
            {"role": "user", "content": self._user_message(facts)},
        ]

    @abstractmethod
    def _user_message(self, facts: dict) -> str:
        raise NotImplementedError


class PartialDependenceInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a partial dependence curve's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.partial_dependence.PartialDependence.insight_facts``
    (feature, target, trend, values).
    """

    def _user_message(self, facts: dict) -> str:
        return (
            f"A partial dependence curve for feature '{facts['feature']}' "
            f"on class '{facts['target']}' goes from "
            f"{facts['start_value']} to {facts['end_value']}, with "
            f"predicted probability going from {facts['start_pred']} to "
            f"{facts['end_pred']} (trend classified as "
            f"'{facts['trend']}', ranging between {facts['min_pred']} "
            f"and {facts['max_pred']}). Give a brief analysis of what "
            "this could mean."
        )


class RegressionPartialDependenceInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a regression partial dependence curve's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.regression_partial_dependence.RegressionPartialDependence.insight_facts``
    (feature, output_column, trend, values).
    """

    def _user_message(self, facts: dict) -> str:
        return (
            f"A partial dependence curve for feature '{facts['feature']}' "
            f"on the regression output '{facts['output_column']}' goes "
            f"from {facts['start_value']} to {facts['end_value']}, with "
            f"predicted {facts['output_column']} going from "
            f"{facts['start_pred']} to {facts['end_pred']} (trend "
            f"classified as '{facts['trend']}', ranging between "
            f"{facts['min_pred']} and {facts['max_pred']}). Give a "
            "brief analysis of what this could mean."
        )


class PermutationFeatureImportanceInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a permutation feature importance ranking's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.permutation_feature_importance.PermutationFeatureImportance.insight_facts``
    (a "Top N features" ranking, split into features with and without a
    measurable effect).
    """

    def _user_message(self, facts: dict) -> str:
        top_list = ", ".join(
            f"{item['feature']} ({item['importance_mean']:.3f})"
            for item in facts["top_features"]
        )
        non_positive = ", ".join(
            item["feature"] for item in facts["non_positive_features"]
        )
        return (
            f"Ranked by the drop in {facts['scoring']} caused by "
            f"shuffling each feature, the top {facts['count']} "
            f"features are: {top_list}. "
            + (
                f"Of these, {non_positive} showed no measurable "
                f"importance (shuffling them did not decrease "
                f"{facts['scoring']}, or even improved it). "
                if non_positive
                else ""
            )
            + "Give a brief analysis of what this ranking could mean."
        )


class RegressionPermutationFeatureImportanceInsightAnalyzer(
    BaseExplainerInsightAnalyzer
):
    """Turns a regression permutation feature importance ranking into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.regression_permutation_feature_importance.RegressionPermutationFeatureImportance.insight_facts``
    (the top-3 features ranked by importance, split into features with and
    without a measurable effect).
    """

    def _user_message(self, facts: dict) -> str:
        top_list = ", ".join(
            f"{item['feature']} ({item['importance_mean']:.3f})"
            for item in facts["top_features"]
        )
        non_positive = ", ".join(
            item["feature"] for item in facts["non_positive_features"]
        )
        return (
            f"Ranked by the drop in {facts['scoring']} caused by "
            f"shuffling each feature, the top 3 features for this "
            f"regression model are: {top_list}. "
            + (
                f"Of these, {non_positive} showed no measurable "
                f"importance (shuffling them did not decrease "
                f"{facts['scoring']}, or even improved it). "
                if non_positive
                else ""
            )
            + "Give a brief analysis of what this ranking could mean."
        )


class KernelShapInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns one explained instance's SHAP attributions into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.kernel_shap.KernelShap.insight_facts``
    (predicted class/probability plus the top-3 SHAP contributors).
    """

    def _user_message(self, facts: dict) -> str:
        contributors = "; ".join(
            f"{item['feature']} ({item['shap_value']:+.3f})"
            for item in facts["top_features"]
        )
        return (
            f"For one instance, a Kernel SHAP explainer predicted "
            f"class '{facts['predicted_name']}' with probability "
            f"{facts['predicted_prob']:.2f}. The top contributing "
            f"features (SHAP values) were: {contributors}. Positive "
            "SHAP values push the prediction toward "
            f"'{facts['predicted_name']}', negative values push it "
            "away. Give a brief analysis of what this could mean."
        )


class RegressionKernelShapInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns one explained instance's regression SHAP attributions into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.regression_kernel_shap.RegressionKernelShap.insight_facts``
    (predicted value, baseline offset, and the top-3 SHAP contributors).
    """

    def _user_message(self, facts: dict) -> str:
        contributors = "; ".join(
            f"{item['feature']}={item['value']} ({item['shap_value']:+.3f})"
            for item in facts["top_features"]
        )
        return (
            f"For one instance, a Kernel SHAP regression explainer "
            f"predicted {facts['output_column']}={facts['prediction']}, "
            f"a delta of {facts['delta']:+} from the baseline "
            f"{facts['base_value']}. The top contributing features "
            f"(SHAP values) were: {contributors}. Positive SHAP "
            "values push the prediction above the baseline, negative "
            "values push it below. Give a brief analysis of what "
            "this could mean."
        )


class ContrastiveShapInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a contrastive SHAP explanation's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.contrastive_shap.ContrastiveShap.insight_facts``
    (fact/foil class names and probabilities, plus the top features by
    ``|fact - foil|`` attribution).
    """

    def _user_message(self, facts: dict) -> str:
        top_features = ", ".join(
            f"{item['feature']}={item['value']} (delta={item['delta']})"
            for item in facts["top_features"]
        )
        return (
            f"A contrastive SHAP explanation shows the model predicted "
            f"'{facts['fact_name']}' (p={facts['fact_prob']}) rather than "
            f"the foil class '{facts['foil_name']}' (p={facts['foil_prob']}). "
            f"The features that most pushed the prediction towards the "
            f"fact class and away from the foil, ranked by absolute "
            f"attribution difference (fact minus foil), are: "
            f"{top_features}. Give a brief analysis of what this "
            "contrast could mean."
        )


class LimeTextInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a LIME text instance's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.lime_text.LimeText.insight_facts``
    (predicted class, probability, top influential words with their signed
    weight).
    """

    def _user_message(self, facts: dict) -> str:
        top_words = ", ".join(
            f"'{word}' ({weight:+})" for word, weight in facts["top_words"]
        )
        return (
            f"A LIME text explanation for the text '{facts['text']}' "
            f"predicted the class '{facts['predicted_name']}' with "
            f"probability {facts['predicted_prob']}. The most "
            f"influential words, ranked by absolute LIME weight, "
            f"were: {top_words} (positive weight pushes the "
            "prediction towards the predicted class, negative "
            "weight pushes away from it). Give a brief analysis of "
            "what this could mean."
        )


class TokenAblationInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a token-ablation instance's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.token_ablation.TokenAblation.insight_facts``
    (predicted class, probability, top influential tokens with their
    probability drop when ablated).
    """

    def _user_message(self, facts: dict) -> str:
        top_tokens = ", ".join(
            f"'{token}' ({importance:+})" for token, importance in facts["top_tokens"]
        )
        return (
            f"A token-ablation explanation for the text "
            f"'{facts['text']}' predicted the class "
            f"'{facts['predicted_name']}' with probability "
            f"{facts['predicted_prob']}. The most influential "
            f"tokens, ranked by absolute probability drop when "
            f"removed one at a time, were: {top_tokens} (a positive "
            "value means removing that token decreased the "
            "predicted probability, i.e. the model relied on it; a "
            "negative value means removing it increased the "
            "probability). Give a brief analysis of what this could "
            "mean."
        )


class DiceCounterfactualInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a DiCE counterfactual instance's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.dice_counterfactual.DiceCounterfactual.insight_facts``
    (predicted class/probability and the synthetic counterfactuals found).
    """

    def _user_message(self, facts: dict) -> str:
        counterfactuals = facts["counterfactuals"]
        if counterfactuals:
            cf_lines = "\n".join(
                f"- Changing {', '.join(cf['changed_features']) or 'nothing'} "
                f"yields '{cf['cf_name']}'."
                for cf in counterfactuals
            )
        else:
            cf_lines = "No counterfactuals could be generated for this instance."
        return (
            f"The model predicted '{facts['predicted_name']}' "
            f"(p={facts['predicted_prob']}) for this instance. DiCE "
            "generated the following synthetic counterfactuals, each "
            "describing a minimal set of feature changes that would "
            f"flip the prediction:\n{cf_lines}\n"
            "Give a brief analysis of what these changes suggest "
            "about the model's decision boundary."
        )


class NearestCounterfactualInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a nearest-counterfactual instance's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.nearest_counterfactual.NearestCounterfactual.insight_facts``
    (predicted class/probability and the nearest real training examples
    classified differently).
    """

    def _user_message(self, facts: dict) -> str:
        counterfactuals = facts["counterfactuals"]
        if counterfactuals:
            cf_lines = "\n".join(
                f"- Changing {', '.join(cf['changed_features']) or 'nothing'} "
                f"yields '{cf['cf_name']}' (distance {cf['distance']})."
                for cf in counterfactuals
            )
        else:
            cf_lines = "No counterfactual examples were found in the training data."
        return (
            f"The model predicted '{facts['predicted_name']}' "
            f"(p={facts['predicted_prob']}) for this instance. The "
            "following real training examples, classified "
            "differently, are the nearest counterfactuals found "
            f"(ranked by distance to the instance):\n{cf_lines}\n"
            "Give a brief analysis of what changes in these features "
            "would most plausibly lead to a different prediction."
        )


class GradCamInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns a Grad-CAM image explanation's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.grad_cam.GradCam.insight_facts``
    (predicted class, probability, dominant activation region, coverage).
    """

    def _user_message(self, facts: dict) -> str:
        return (
            "A Grad-CAM class activation map for an image classifier "
            f"shows the model predicted '{facts['predicted_name']}' "
            f"(p={facts['predicted_prob']}). The activations that "
            f"most supported this prediction are concentrated in "
            f"the {facts['dominant_region']} region of the image, "
            f"with about {facts['coverage_ratio'] * 100:.0f}% of the "
            "image reaching a comparably high activation (a low "
            "percentage means a small, localised hotspot; a high "
            "percentage means the influence is spread across the "
            "image). Give a brief analysis of what this could mean."
        )


class OcclusionSaliencyInsightAnalyzer(BaseExplainerInsightAnalyzer):
    """Turns an Occlusion Saliency image explanation's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.occlusion_saliency.OcclusionSaliency.insight_facts``
    (predicted class, probability, dominant occlusion region, coverage).
    """

    def _user_message(self, facts: dict) -> str:
        return (
            "An Occlusion Saliency map for an image classifier "
            f"shows the model predicted '{facts['predicted_name']}' "
            f"(p={facts['predicted_prob']}). Occluding the "
            f"{facts['dominant_region']} region of the image caused "
            "the largest drop in that predicted probability, with "
            f"about {facts['coverage_ratio'] * 100:.0f}% of the "
            "image causing a comparably large drop when occluded "
            "(a low percentage means the model relies on a small, "
            "localised area; a high percentage means the evidence "
            "is spread across the image). Give a brief analysis of "
            "what this could mean."
        )


EXPLAINER_INSIGHT_ANALYZERS: Dict[str, Type[BaseInsightAnalyzer]] = {
    "PartialDependence": PartialDependenceInsightAnalyzer,
    "RegressionPartialDependence": RegressionPartialDependenceInsightAnalyzer,
    "PermutationFeatureImportance": PermutationFeatureImportanceInsightAnalyzer,
    "RegressionPermutationFeatureImportance": (
        RegressionPermutationFeatureImportanceInsightAnalyzer
    ),
    "KernelShap": KernelShapInsightAnalyzer,
    "RegressionKernelShap": RegressionKernelShapInsightAnalyzer,
    "ContrastiveShap": ContrastiveShapInsightAnalyzer,
    "LimeText": LimeTextInsightAnalyzer,
    "TokenAblation": TokenAblationInsightAnalyzer,
    "DiceCounterfactual": DiceCounterfactualInsightAnalyzer,
    "NearestCounterfactual": NearestCounterfactualInsightAnalyzer,
    "GradCam": GradCamInsightAnalyzer,
    "OcclusionSaliency": OcclusionSaliencyInsightAnalyzer,
}
