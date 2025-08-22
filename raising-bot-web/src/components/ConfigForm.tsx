import React from "react";
import { Box, Typography, TextField, Button, Stack, CircularProgress, MenuItem } from "@mui/material";

const ORDER_TYPES = [
  "SNAP MID", "LMT", "MKT"
];

const CONFIG_FIELDS = [
  { key: "IBKR_ACCOUNT", label: "IBKR Account Number", required: true },
  { key: "IBKR_PORT", label: "IBKR Port", required: true, helper: "Live account is 7496, Paper account is 7497, please confirm it yourself" },
  { key: "TELEGRAM_API_ID", label: "Telegram API ID", required: false, helper: "Optional" },
  { key: "TELEGRAM_API_HASH", label: "Telegram API Hash", required: false, helper: "Optional" },
  { key: "TELEGRAM_CHANNEL", label: "Telegram Channel", required: false, helper: "Optional" },
  { key: "IBKR_HOST", label: "IBKR Host", required: true, helper: "Usually '127.0.0.1'" },
  { key: "IBKR_CLIENT_ID", label: "IBKR Client ID", required: true, helper: "Just put in a random number" },
  { key: "DEFAULT_ORDER_TYPE", label: "Default Order Type", required: true, helper: "Choose a valid IBKR order type" },
  { key: "SNAPMID_OFFSET", label: "SnapMid Offset", required: true, helper: "Offset for SnapMid orders" },
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
              orderType === "SNAP MID" && (
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
            ) : (
              <TextField
                key={key}
                label={label}
                value={config[key] || ""}
                required={required}
                helperText={helper}
                onChange={(e) => onFieldChange(key, e.target.value)}
                variant="outlined"
                fullWidth
                type={key === "TELEGRAM_API_HASH" ? "password" : "text"}
              />
            )
          )}
          {/* Conditional fields for limit/stop price */}
          {orderType === "LMT" && (
            <TextField
              label="Default Limit Price"
              value={config.DEFAULT_LIMIT_PRICE || ""}
              required
              onChange={(e) => onFieldChange("DEFAULT_LIMIT_PRICE", e.target.value)}
              variant="outlined"
              fullWidth
              helperText="Required for LMT orders"
            />
          )}
          {/* {orderType === "STP" && (
            <TextField
              label="Default Stop Price"
              value={config.DEFAULT_STOP_PRICE || ""}
              required
              onChange={(e) => onFieldChange("DEFAULT_STOP_PRICE", e.target.value)}
              variant="outlined"
              fullWidth
              helperText="Required for STP orders"
            />
          )}
          {orderType === "STP LMT" && (
            <>
              <TextField
                label="Default Limit Price"
                value={config.DEFAULT_LIMIT_PRICE || ""}
                required
                onChange={(e) => onFieldChange("DEFAULT_LIMIT_PRICE", e.target.value)}
                variant="outlined"
                fullWidth
                helperText="Required for STP LMT orders"
              />
              <TextField
                label="Default Stop Price"
                value={config.DEFAULT_STOP_PRICE || ""}
                required
                onChange={(e) => onFieldChange("DEFAULT_STOP_PRICE", e.target.value)}
                variant="outlined"
                fullWidth
                helperText="Required for STP LMT orders"
              />
            </>
          )} */}
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
