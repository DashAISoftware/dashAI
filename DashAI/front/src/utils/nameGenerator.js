export function generateSequentialName({
  base,
  items = [],
  getName = (item) => item.name,
  filter = () => true,
  allowExtension = false, // útil para .json
  startAt = 1,
}) {
  const escapedBase = base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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

  const generatedName = `${base}_${next}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
}
