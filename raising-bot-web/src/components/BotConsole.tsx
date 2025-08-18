import React, { useRef, useEffect, useState } from "react";
import { Box, Button, Typography, TextField } from "@mui/material";

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
  const [sessionExists, setSessionExists] = useState<boolean | null>(null);
  const [clearing, setClearing] = useState(false);
  const [hasTelegramConfig, setHasTelegramConfig] = useState(false); // NEW

  useEffect(() => {
    if (output.length > prevLengthRef.current && endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
    prevLengthRef.current = output.length;
  }, [output]);

  // Load config to see if Telegram is configured
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/config");
        if (!r.ok) return;
        const d = await r.json();
        const id = (d?.TELEGRAM_API_ID ?? "").toString().trim();
        setHasTelegramConfig(!!id);
      } catch { /* ignore */ }
    };
    load();
  }, []);

  // Check current telegram session presence only if Telegram is configured
  useEffect(() => {
    if (!hasTelegramConfig) {
      setSessionExists(null);
      return;
    }
    const check = async () => {
      try {
        const r = await fetch("/api/telegram/session");
        if (r.ok) {
          const d = await r.json();
          setSessionExists(!!d.exists);
        }
      } catch { /* ignore */ }
    };
    check();
  }, [hasTelegramConfig]);

  const clearTelegramSession = async () => {
    if (!hasTelegramConfig) return;
    if (botRunning || botLoading) return;
    if (!window.confirm("Clear Telegram session? You will need to login again.")) return;
    setClearing(true);
    try {
      const r = await fetch("/api/telegram/session", { method: "DELETE" });
      if (r.ok) {
        setSessionExists(false);
      } else {
        const d = await r.json().catch(() => ({}));
        alert(d.error || "Failed to clear session.");
      }
    } catch {
      alert("Network error clearing session.");
    } finally {
      setClearing(false);
    }
  };

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

      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <Button variant="contained" disabled={botRunning || botLoading} onClick={startBot}>
          Start Bot
        </Button>
        <Button color="error" variant="contained" disabled={!botRunning || botLoading} onClick={stopBot}>
          Stop Bot
        </Button>

        {hasTelegramConfig && (
          <>
            <Button
              variant="outlined"
              disabled={botRunning || botLoading || clearing}
              onClick={clearTelegramSession}
              title={botRunning ? "Stop the bot before clearing the session" : "Clear Telegram session"}
            >
              {clearing ? "Clearing..." : "Clear Telegram Session"}
            </Button>
            {sessionExists === false && (
              <Typography sx={{ ml: 1, alignSelf: "center" }} color="warning.main">
                No Telegram session found — first run will ask to login.
              </Typography>
            )}
          </>
        )}
      </Box>

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
