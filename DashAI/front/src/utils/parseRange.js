const rangeRegex = /^(\d+)(-(\d+))*(,(\d+)(-(\d+))*)*$/;

/**
 * Parses a range string to an array of indexes
 * @param {string} range - The range string to parse (e.g., "1-3,5,7-9")
 * @param {number} maxValue - The maximum value allowed for the indexes
 * @returns {number[]} - An array of indexes
 * @throws {Error} - If the range string is invalid or contains values greater than maxValue
 */
export function parseRangeToIndex(range, maxValue) {
  const indexArray = [];
  if (!rangeRegex.test(range)) {
    throw new Error("The entered text doesn't fit the example format");
  }
  const ranges = range.split(",");
  ranges.forEach((range) => {
    const [min, max] = range.split("-");
    if (!range.includes("-") && parseInt(range) <= maxValue) {
      indexArray.push(parseInt(range));
    } else if (
      (!range.includes("-") && parseInt(range) > maxValue) ||
      parseInt(max) > maxValue
    ) {
      throw new Error(
        "The indexes should be minor than the total of columns or rows",
      );
    } else if (parseInt(min) > parseInt(max)) {
      throw new Error(
        "The second number of a range must be greater than the first",
      );
    } else {
      for (let i = parseInt(min); i <= parseInt(max); i++) {
        indexArray.push(i);
      }
    }
  });
  return indexArray;
}
