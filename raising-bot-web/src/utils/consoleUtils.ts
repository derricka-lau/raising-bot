export const stripTimestamp = (line: string) => line.replace(/^\[TS:[^\]]+\]\s*/, "");

export const dedupeCountdowns = (lines: string[]) => {
  const countdownPrefix = "Waiting for market open:";
  const countdownLines = lines.filter(l => stripTimestamp(l).startsWith(countdownPrefix));
  const otherLines = lines.filter(l => !stripTimestamp(l).startsWith(countdownPrefix));
  return countdownLines.length > 0
    ? [...otherLines, countdownLines[countdownLines.length - 1]]
    : lines;
};