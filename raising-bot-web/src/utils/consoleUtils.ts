export const stripTimestamp = (line: string) => line.replace(/^\[TS:[^\]]+\]\s*/, "");

export const dedupeCountdowns = (lines: string[]) => {
  const countdownPrefixs = ["Waiting for market open:", "Live SPX Price:"];
  const countdownLines = lines.filter(l => countdownPrefixs.some(prefix => stripTimestamp(l).startsWith(prefix)));
  const otherLines = lines.filter(l => !countdownPrefixs.some(prefix => stripTimestamp(l).startsWith(prefix)));
  return countdownLines.length > 0
    ? [...otherLines, countdownLines[countdownLines.length - 1]]
    : lines;
};