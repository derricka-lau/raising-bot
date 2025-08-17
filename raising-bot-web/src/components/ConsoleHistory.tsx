import React from "react";
import { Box, Typography } from "@mui/material";

interface ConsoleHistoryProps {
  output: { text: string; fromUser?: boolean }[];
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
        output.map((msg, i) => (
          <Box
            key={i}
            sx={{
              mb: 1,
              alignSelf: msg.fromUser ? "flex-end" : "flex-start",
              background: msg.fromUser ? "#bbf7d0" : "#e3f2fd",
              px: 2,
              py: 1,
              borderRadius: 2,
              fontFamily: "monospace",
              fontSize: 15,
            }}
          >
            {msg.text}
          </Box>
        ))
      )}
    </Box>
  </Box>
);

export default ConsoleHistory;
