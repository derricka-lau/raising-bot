import React, { useEffect, useState } from "react";
import { Box, Typography, TextField } from "@mui/material";
import { stripTimestamp } from "../utils/consoleUtils";

const todayStr = new Date().toISOString().slice(0, 10);

const ConsoleHistory: React.FC = () => {
  const [history, setHistory] = useState<string[]>([]);
  const [date, setDate] = useState<string>(todayStr); // Default to today

  useEffect(() => {
    const params = date ? `?date=${date}` : "";
    fetch(`/api/history${params}`)
      .then((res) => res.json())
      .then((data) => {
        setHistory(
          data.history.filter(
            (line: string) =>
              !stripTimestamp(line).startsWith("Waiting for market open:") &&
              !stripTimestamp(line).startsWith("Live SPX Price:")
          )
        );
      });
  }, [date]);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Console History
      </Typography>
      <TextField
        label="Filter by date"
        type="date"
        size="small"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        sx={{ mb: 2 }}
        InputLabelProps={{ shrink: true }}
      />
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
        {history.length === 0 ? (
          <Typography color="grey.600">No history yet.</Typography>
        ) : (
          history.map((line, i) => (
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
