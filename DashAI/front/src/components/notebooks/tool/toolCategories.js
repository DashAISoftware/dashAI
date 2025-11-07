/**
 * Utility: group tools by category.
 * Falls back to "Other" when category is missing.
 */
export function groupByCategory(tools) {
  const groups = tools.reduce((acc, tool) => {
    const cat = tool?.metadata?.category || "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(tool);
    return acc;
  }, {});
  return groups;
}

export const PREFERRED_ORDER = [
  "Basic Preprocessing",
  "Encoding",
  "Scaling & Normalization",
  "Dimensionality Reduction",
  "Feature Selection",
  "Polynomial & Kernel Methods",
  "Resampling & Class Balancing",
  "Pipelines & Meta-Converters",
  "Advanced / Specialized",
  "Other",
];

export function sortCategories(catNames) {
  const set = new Set(PREFERRED_ORDER);
  const preferred = catNames.filter((c) => set.has(c));
  const remaining = catNames.filter((c) => !set.has(c)).sort();
  return [
    ...PREFERRED_ORDER.filter((c) => preferred.includes(c)),
    ...remaining,
  ];
}
