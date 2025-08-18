import React from "react";
import { Box, Typography } from "@mui/material";
import { stripTimestamp } from "../utils/consoleUtils";

interface ConsoleHistoryProps {
  output: string[];
}

const ConsoleHistory: React.FC<ConsoleHistoryProps> = ({ output }) => {
  // Remove countdown lines from history (keep only non-countdown lines)
  const filteredOutput = output.filter(
    (line) => !stripTimestamp(line).startsWith("Waiting for market open:") && !stripTimestamp(line).startsWith("Live SPX Price:")
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Console History
      </Typography>
      <Box
        sx={{
          background: "#fafafa",
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
              {line}
            </Box>
          ))
        )}
      </Box>
    </Box>
  );
};

export default ConsoleHistory;
