import React from "react";
import { Box, Typography, TextField, Button, Stack, CircularProgress, MenuItem } from "@mui/material";

const ORDER_TYPES = [
  "SNAP MID", "LMT", "MKT", "PEG MID"
];

const CONFIG_FIELDS = [
  { key: "IBKR_ACCOUNT", label: "IBKR Account Number", required: true },
  { key: "IBKR_PORT", label: "IBKR Port", required: true, helper: "Live account is 7496, Paper account is 7497, please confirm it yourself" },
  { key: "TELEGRAM_API_ID", label: "Telegram API ID", required: false },
  { key: "TELEGRAM_API_HASH", label: "Telegram API Hash", required: false },
  { key: "TELEGRAM_CHANNEL", label: "Telegram Channel", required: false, helper: "Optional, e.g. @RaisingCycle_Notification_bot" },
  { key: "IBKR_HOST", label: "IBKR Host", required: true, helper: "Usually '127.0.0.1'" },
  { key: "IBKR_CLIENT_ID", label: "IBKR Client ID", required: true, helper: "Just put in a random number" },
  { key: "SNAPMID_OFFSET", label: "Midpoint Offset", required: true, helper: "Offset for SNAP MID and PEG MID orders" },
  { key: "DEFAULT_ORDER_TYPE", label: "Default Order Type", required: true, helper: "Choose a valid IBKR order type" },
  { key: "LMT_PRICE_FOR_SPREAD_30", label: "Price Cap for 30-wide Spreads (LMT/PEG MID)", required: false, helper: "Optional. Used for both LMT and PEG MID." },
  { key: "LMT_PRICE_FOR_SPREAD_35", label: "Price Cap for 35-wide Spreads (LMT/PEG MID)", required: false, helper: "Optional. Used for both LMT and PEG MID." },
  { key: "WAIT_AFTER_OPEN_SECONDS", label: "Wait After Open (seconds)", required: false, helper: "Seconds to wait after market open before fetching SPX open price. Increase if there is latency or low liquidity." }
];

interface ConfigFormProps {
  config: Record<string, string>;
  onFieldChange: (key: string, value: string) => void;
  onSave: () => void;
  saving: boolean;
}

const ConfigForm: React.FC<ConfigFormProps> = ({ config, onFieldChange, onSave, saving }) => {
  const orderType = (config.DEFAULT_ORDER_TYPE || "").toUpperCase();

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Configuration
      </Typography>
      <Box component="form" noValidate autoComplete="off">
        <Stack spacing={2}>
          {CONFIG_FIELDS.map(({ key, label, required, helper }) =>
            key === "DEFAULT_ORDER_TYPE" ? (
              <TextField
                key={key}
                select
                label={label}
                value={config[key] || ""}
                required={required}
                helperText={helper || "Choose a valid IBKR order type"}
                onChange={(e) => onFieldChange(key, e.target.value)}
                variant="outlined"
                fullWidth
              >
                <MenuItem value="">Select...</MenuItem>
                {ORDER_TYPES.map((type) => (
                  <MenuItem key={type} value={type}>{type}</MenuItem>
                ))}
              </TextField>
            ) : key === "SNAPMID_OFFSET" ? (
              (orderType === "SNAP MID" || orderType === "PEG MID") && (
                <TextField
                  key={key}
                  label={label}
                  value={config[key] || ""}
                  required={required}
                  helperText={helper}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                  variant="outlined"
                  fullWidth
                />
              )
            ) : key === "LMT_PRICE_FOR_SPREAD_30" || key === "LMT_PRICE_FOR_SPREAD_35" ? (
              (orderType === "LMT" || orderType === "PEG MID") && (
                <TextField
                  key={key}
                  label={label}
                  value={config[key] || ""}
                  required={required}
                  helperText={helper}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                  variant="outlined"
                  fullWidth
                  type="number"
                />
              )
            ) : key === "WAIT_AFTER_OPEN_SECONDS" ? (
              <TextField
                label="Wait After Open (seconds)"
                name="WAIT_AFTER_OPEN_SECONDS"
                type="number"
                value={config.WAIT_AFTER_OPEN_SECONDS ?? 3}
                onChange={(e) => onFieldChange("WAIT_AFTER_OPEN_SECONDS", e.target.value)}
                InputProps={{ inputProps: { min: 1, max: 61 } }}
                helperText="Seconds to wait after market open before fetching SPX open price."
                fullWidth
              />
            ) : (
              <TextField
                key={key}
                label={label}
                value={config[key] || ""}
                required={required}
                helperText={
                  key === "TELEGRAM_API_ID" || key === "TELEGRAM_API_HASH"
                    ? (
                        <span>
                          Optional, see&nbsp;
                          <a
                            href="https://core.telegram.org/api/obtaining_api_id"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Telegram API documentation (Obtaining api_id)
                          </a>
                        </span>
                      )
                    : helper
                }
                onChange={(e) => onFieldChange(key, e.target.value)}
                variant="outlined"
                fullWidth
                type={key === "TELEGRAM_API_HASH" || key === "TELEGRAM_API_ID" ? "password" : "text"}
              />
            )
          )}
          {/* Conditional fields for limit/stop price */}
          {(orderType === "LMT" || orderType === "PEG MID") && !config.LMT_PRICE_FOR_SPREAD_30 && !config.LMT_PRICE_FOR_SPREAD_35 && (
            <TextField
              label="Default Price Cap (LMT/PEG MID)"
              value={config.DEFAULT_LIMIT_PRICE || ""}
              required
              onChange={(e) => onFieldChange("DEFAULT_LIMIT_PRICE", e.target.value)}
              variant="outlined"
              fullWidth
              helperText="Required if spread-specific caps are not set."
            />
          )}
          <Box>
            <Button
              variant="contained"
              color="primary"
              onClick={onSave}
              disabled={saving}
              sx={{ mr: 2 }}
            >
              {saving ? <CircularProgress size={24} /> : "Save Config"}
            </Button>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default ConfigForm;
