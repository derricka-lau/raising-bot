import React from "react";
import { Box, Typography, TextField, Button, Stack, CircularProgress } from "@mui/material";

const CONFIG_FIELDS = [
  { key: "IBKR_ACCOUNT", label: "IBKR Account Number", required: true },
  { key: "IBKR_PORT", label: "IBKR Port", required: true },
  { key: "TELEGRAM_API_ID", label: "Telegram API ID", required: false, helper: "Optional" },
  { key: "TELEGRAM_API_HASH", label: "Telegram API Hash", required: false, helper: "Optional" },
  { key: "TELEGRAM_CHANNEL", label: "Telegram Channel", required: false, helper: "Optional" },
  { key: "IBKR_HOST", label: "IBKR Host", required: true },
  { key: "IBKR_CLIENT_ID", label: "IBKR Client ID", required: true },
  { key: "UNDERLYING_SYMBOL", label: "Underlying Symbol", required: true },
  { key: "DEFAULT_ORDER_TYPE", label: "Default Order Type", required: true },
  { key: "SNAPMID_OFFSET", label: "SnapMid Offset", required: true },
];

interface ConfigFormProps {
  config: Record<string, string>;
  onFieldChange: (key: string, value: string) => void;
  onSave: () => void;
  saving: boolean;
}

const ConfigForm: React.FC<ConfigFormProps> = ({ config, onFieldChange, onSave, saving }) => (
  <Box>
    <Typography variant="h6" gutterBottom>
      Configuration
    </Typography>
    <Box component="form" noValidate autoComplete="off">
      <Stack spacing={2}>
        {CONFIG_FIELDS.map(({ key, label, required, helper }) => (
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
        ))}
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

export default ConfigForm;
