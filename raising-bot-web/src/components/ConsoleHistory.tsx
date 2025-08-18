import React, { useMemo } from "react";
import { Box, Typography } from "@mui/material";
import { stripTimestamp, dedupeCountdowns } from "../utils/consoleUtils";

interface ConsoleHistoryProps {
  output: string[];
}

const ConsoleHistory: React.FC<ConsoleHistoryProps> = ({ output }) => {
  // Deduplicate countdowns and strip timestamps
  const dedupedOutput = useMemo(() => dedupeCountdowns(output), [output]);
  // Remove countdown lines from history (keep only non-countdown lines)
  const filteredOutput = dedupedOutput.filter(
    (line) => !stripTimestamp(line).startsWith("Waiting for market open:")
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Console History
      </Typography>
      <Box
        sx={{
          background: "#fafafa",
          height: 1000,
          overflowY: "auto",
          p: 2,
          borderRadius: 2,
          border: "1px solid #e0e0e0",
          fontFamily: "monospace",
          fontSize: 15,
        }}
      >
        {filteredOutput.length === 0 ? (
          <Typography color="grey.600">No history yet.</Typography>
        ) : (
          filteredOutput.map((line, i) => (
            <Box key={i} sx={{ mb: 1 }}>
              {stripTimestamp(line)}
            </Box>
          ))
        )}
      </Box>
    </Box>
  );
};

export default ConsoleHistory;
