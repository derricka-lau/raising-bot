import { useEffect, useState, useCallback } from "react";
import { Container, Paper, Tabs, Tab, Snackbar, Alert } from "@mui/material";
import ConfigForm from "./components/ConfigForm";
import BotConsole from "./components/BotConsole";
import ConsoleHistory from "./components/ConsoleHistory";



function App() {
  const [tab, setTab] = useState(0);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [output, setOutput] = useState<string[]>([]);
  const [botRunning, setBotRunning] = useState(false);
  const [botLoading, setBotLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({ open: false, message: "", severity: "success" });
  const [inputValue, setInputValue] = useState("");

  // Helpers
  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const isAbortError = (e: unknown) =>
    e instanceof DOMException
      ? e.name === "AbortError"
      : typeof e === "object" && e !== null && "name" in e && (e as { name?: string }).name === "AbortError";

  const fetchWithRetry = async (input: RequestInfo, init?: RequestInit, attempts = 3, baseDelay = 400): Promise<Response> => {
    let err: unknown;
    for (let i = 0; i < attempts; i++) {
      try {
        const res = await fetch(input, init);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res;
      } catch (e: unknown) {
        err = e;
        if (i < attempts - 1) await sleep(baseDelay * 2 ** i);
      }
    }
    throw err;
  };

  const confirmRunning = async (expect: boolean, timeoutMs = 5000): Promise<boolean> => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const r = await fetch("/api/status");
        if (!r.ok) break;
        const d: { running?: boolean } = await r.json();
        if (typeof d.running === "boolean" && d.running === expect) return true;
      } catch {
        // Ignore errors
      }
      await sleep(400);
    }
    return false;
  };

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const init = async () => {
      // config with retry
      try {
        const r = await fetchWithRetry("/api/config", { signal: controller.signal });
        const data = await r.json();
        if (mounted) setConfig(data);
      } catch (e) {
        if (!isAbortError(e)) setSnackbar({ open: true, message: "Failed to load config.", severity: "error" });
      }
      // status with retry
      try {
        const r = await fetchWithRetry("/api/status", { signal: controller.signal });
        const data: { running?: boolean } = await r.json();
        if (mounted && typeof data.running === "boolean") setBotRunning(data.running);
      } catch (e) {
        if (!isAbortError(e)) setSnackbar({ open: true, message: "Failed to load status.", severity: "error" });
      }
    };

    // Output polling with backoff
    let cancelled = false;
    let timeoutId: number | undefined;
    let delay = 1000;

    const poll = async () => {
      try {
        const r = await fetch("/api/output");
        if (!r.ok) throw new Error("Output HTTP error");
        const data: { output?: string[] } = await r.json();
        if (!cancelled) {
          setOutput((prev) => {
            const newLines: string[] = data.output || [];
            if (newLines.length === prev.length) return prev;
            // Update countdown in place
            const last = newLines[newLines.length - 1] || "";
            if (last.startsWith("Waiting for market open:")) {
              const prevWithoutCountdown = prev.filter((l) => !l.startsWith("Waiting for market open:"));
              return [...prevWithoutCountdown, last];
            }
            return newLines;
          });
        }
        delay = 1000; // reset on success
      } catch (e) {
        if (!isAbortError(e)) {
          // exponential backoff up to 15s
          delay = Math.min(delay * 2, 15000);
        }
      } finally {
        if (!cancelled) {
          timeoutId = window.setTimeout(poll, delay);
        }
      }
    };

    init().then(() => poll());
    return () => {
      mounted = false;
      cancelled = true;
      controller.abort();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  // ConfigForm handlers
  const saveConfig = async () => {
    setSaving(true);
    try {
      const r = await fetchWithRetry("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (r.ok) setSnackbar({ open: true, message: "Config saved!", severity: "success" });
      else setSnackbar({ open: true, message: "Failed to save config.", severity: "error" });
    } catch (e) {
      console.error("Error saving config:", e);
      setSnackbar({ open: true, message: "Network error saving config.", severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  // BotConsole handlers with retries + verification
  const startBot = async () => {
    setBotLoading(true);
    try {
      await fetchWithRetry("/api/start", { method: "POST" }, 3);
      const ok = await confirmRunning(true, 6000);
      setBotRunning(ok);
      if (!ok) setSnackbar({ open: true, message: "Bot failed to start.", severity: "error" });
      // Ensure spinner is visible for at least 500ms
      await sleep(500);
    } catch {
      setSnackbar({ open: true, message: "Failed to start bot.", severity: "error" });
      await sleep(500);
    } finally {
      setBotLoading(false);
    }
  };

  const resetBotState = useCallback(() => {
    setBotRunning(false);
    setOutput([]);
    setInputValue("");
    // Optionally reset config, snackbar, etc.
  }, []);

  const stopBot = async () => {
    setBotLoading(true);
    try {
      await fetchWithRetry("/api/stop", { method: "POST" }, 3);
      const ok = await confirmRunning(false, 6000);
      setBotRunning(!ok ? botRunning : false);
      if (!ok) setSnackbar({ open: true, message: "Bot did not stop.", severity: "error" });
      // Reset state after stopping
      resetBotState();
    } catch {
      setSnackbar({ open: true, message: "Failed to stop bot.", severity: "error" });
    } finally {
      setBotLoading(false);
    }
  };

  const sendInput = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    try {
      await fetchWithRetry("/api/input", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: trimmed }),
      }, 3);
    } catch {
      setSnackbar({ open: true, message: "Failed to send input.", severity: "error" });
    } finally {
      setInputValue("");
    }
  };

  // Field change handler for ConfigForm
  const handleFieldChange = useCallback((key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  }, []);

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