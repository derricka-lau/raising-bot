import React from "react";
import { Box, Typography } from "@mui/material";

interface ConsoleHistoryProps {
  output: string[];
}

const ConsoleHistory: React.FC<ConsoleHistoryProps> = ({ output }) => (
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
      {output.length === 0 ? (
        <Typography color="grey.600">No history yet.</Typography>
      ) : (
        output.map((line, i) => (
          <Box key={i} sx={{ mb: 1 }}>
            {line}
          </Box>
        ))
      )}
    </Box>
  </Box>
);

export default ConsoleHistory;
