import React, { useRef, useEffect } from "react";
import { Box, Typography, Stack, Button, CircularProgress, TextField } from "@mui/material";

interface BotConsoleProps {
  output: string[];
  botRunning: boolean;
  botLoading: boolean;
  startBot: () => void;
  stopBot: () => void;
  inputValue: string;
  setInputValue: (v: string) => void;
  sendInput: () => void;
}

const BotConsole: React.FC<BotConsoleProps> = ({
  output,
  botRunning,
  botLoading,
  startBot,
  stopBot,
  inputValue,
  setInputValue,
  sendInput,
}) => {
  const endRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef<number>(output.length);

  useEffect(() => {
    if (output.length > prevLengthRef.current && endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
    prevLengthRef.current = output.length;
  }, [output]);

  const bubbleStyle = {
    maxWidth: "80%",
    alignSelf: "flex-start",
    background: "#e3f2fd",
    color: "#222",
    px: 2,
    py: 1,
    borderRadius: 2,
    mb: 1,
    boxShadow: 1,
    fontFamily: "monospace",
    fontSize: 15,
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Bot Console
      </Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Button
          variant="contained"
          color="success"
          onClick={startBot}
          disabled={botRunning || botLoading}
        >
          Start Bot
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={stopBot}
          disabled={!botRunning || botLoading}
        >
          Stop Bot
        </Button>
        {botLoading && <CircularProgress size={24} sx={{ ml: 2 }} />}
      </Stack>
      <Box
        sx={{
          background: "#f5f5f5",
          maxHeight: '400px',
          overflowY: "auto",
          p: 2,
          borderRadius: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          mb: 2,
          border: "1px solid #e0e0e0",
        }}
      >
        {output.length === 0 ? (
          <Typography color="grey.600">No output yet.</Typography>
        ) : (
          <>
            {output.map((line, i) => {
              // Detect and format signal lines
              if (line.startsWith("Processing signal: ")) {
                try {
                  const jsonStr = line.replace("Processing signal: ", "");
                  const signal = JSON.parse(jsonStr);
                  return (
                    <Box key={i} sx={bubbleStyle}>
                      <strong>Processing signal:</strong><br />
                      • Expiry: {signal.expiry}<br />
                      • Long Call Strike: {signal.lc_strike}<br />
                      • Short Call Strike: {signal.sc_strike}<br />
                      • Trigger Price: {signal.trigger_price}<br />
                      • Order Type: {signal.order_type}
                    </Box>
                  );
                } catch {
                  // fallback to raw line
                  return <Box key={i} sx={bubbleStyle}>{line}</Box>;
                }
              }
              // Default: regular line
              return <Box key={i} sx={bubbleStyle}>{line}</Box>;
            })}
            <div ref={endRef} />
          </>
        )}
      </Box>
      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          placeholder="Type your command..."
          fullWidth
          size="small"
          variant="outlined"
          sx={{ background: "#fff", borderRadius: 1 }}
          disabled={!botRunning}
          value={inputValue}
          onChange={e => {
            // Remove any line breaks from input
            const oneLine = e.target.value.replace(/[\r\n]+/g, " ");
            setInputValue(oneLine);
          }}
          onKeyDown={async e => {
            if (e.key === "Enter" && botRunning && inputValue) {
              await sendInput();
            }
          }}
        />
        <Button
          variant="contained"
          disabled={!botRunning || !inputValue}
          onClick={sendInput}
        >
          Send
        </Button>
      </Box>
    </Box>
  );
};

export default BotConsole;
