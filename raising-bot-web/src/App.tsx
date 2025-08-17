import { useEffect, useState } from "react";
import { Container, Paper, Tabs, Tab, Snackbar, Alert } from "@mui/material";
import ConfigForm from "./components/ConfigForm";
import BotConsole from "./components/BotConsole";
import ConsoleHistory from "./components/ConsoleHistory";

function App() {
  const [tab, setTab] = useState(0);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [output, setOutput] = useState<{ text: string; fromUser?: boolean }[]>([]);
  const [botRunning, setBotRunning] = useState(false);
  const [botLoading, setBotLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({ open: false, message: "", severity: "success" });
  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then(setConfig);

    // Check bot status on page load
    fetch("/api/status")
      .then((r) => r.json())
      .then(data => setBotRunning(data.running));

    const interval = setInterval(() => {
      fetch("/api/output")
        .then((r) => r.json())
        .then((data) => setOutput(data.output.map((text: string) => ({ text }))));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // ConfigForm handlers
  const saveConfig = () => {
    setSaving(true);
    fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
      .then((r) => {
        if (r.ok) {
          setSnackbar({ open: true, message: "Config saved!", severity: "success" });
        } else {
          setSnackbar({ open: true, message: "Failed to save config.", severity: "error" });
        }
      })
      .catch(() => setSnackbar({ open: true, message: "Network error.", severity: "error" }))
      .finally(() => setSaving(false));
  };
  const handleFieldChange = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  // BotConsole handlers
  const startBot = async () => {
    setBotLoading(true);
    await fetch("/api/start", { method: "POST" });
    setBotLoading(false);
    setBotRunning(true);
  };
  const stopBot = async () => {
    setBotLoading(true);
    await fetch("/api/stop", { method: "POST" });
    setBotLoading(false);
    setBotRunning(false);
  };
  const sendInput = async () => {
    setOutput(prev => [...prev, { text: inputValue, fromUser: true }]);
    await fetch("/api/input", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: inputValue }),
    });
    setInputValue("");
  };

  return (
    <Container
      maxWidth="md"
      sx={{
        py: 6,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        fontFamily: `"monospace"`,
        fontSize: 15,
        background: "#fafafa",
      }}
    >
      <Paper elevation={4} sx={{ p: 4, mx: "auto", width: "100%", maxWidth: 900 }}>
        <h2 style={{ textAlign: "center", marginBottom: 24, fontFamily: `"monospace"` }}>Raising Bot</h2>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} centered sx={{ mb: 3 }}>
          <Tab label="Config" />
          <Tab label="Bot Console" />
          <Tab label="History" />
        </Tabs>
        {tab === 0 && (
          <ConfigForm
            config={config}
            onFieldChange={handleFieldChange}
            onSave={saveConfig}
            saving={saving}
          />
        )}
        {tab === 1 && (
          <BotConsole
            output={output}
            botRunning={botRunning}
            botLoading={botLoading}
            startBot={startBot}
            stopBot={stopBot}
            inputValue={inputValue}
            setInputValue={setInputValue}
            sendInput={sendInput}
          />
        )}
        {tab === 2 && (
          <ConsoleHistory output={output} />
        )}
      </Paper>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default App;