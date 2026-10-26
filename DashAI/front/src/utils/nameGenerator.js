export function getNextAvailableName(name, existingDatasets) {
  const existingNames = new Set(existingDatasets.map((d) => d.name));
  let i = 1;
  while (existingNames.has(`${name} (${i})`)) i++;
  return `${name} (${i})`;
}

// Turns a display text (e.g. a translated model or task name) into a name
// base: accents are stripped and whitespace runs become a single "_", so
// "Árbol de Decisión" becomes "Arbol_de_Decision".
export function toNameBase(text) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .replace(/\s+/g, "_");
}

export function generateSequentialName({
  base,
  items = [],
  getName = (item) => item.name,
  filter = () => true,
  allowExtension = false, // Whether to allow file extensions (e.g., .json) in the name
  startAt = 1,
}) {
  const nameBase = toNameBase(base);
  const escapedBase = nameBase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const extPart = allowExtension ? "(?:\\.[^.]+)?" : "";
  const regex = new RegExp(`^${escapedBase}_(\\d+)${extPart}$`, "i");

  const numbers = items
    .filter(filter)
    .map((item) => {
      const name = getName(item) || "";
      const match = name.match(regex);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((n) => n !== null);

  const max = numbers.length ? Math.max(...numbers) : startAt - 1;
  const next = max + 1;

  const generatedName = `${nameBase}_${next}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
}
