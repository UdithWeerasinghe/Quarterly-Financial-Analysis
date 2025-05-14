// DrilldownModal.js
// Modal component for displaying detailed drilldown information for a selected metric or data point.
//
// Usage:
//   <DrilldownModal open={open} onClose={handleClose} data={drilldownData} />
//
// Props:
//   open (bool): Whether the modal is open.
//   onClose (function): Callback to close the modal.
//   data (object): The data to display in the modal.

import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, List, ListItem, ListItemText } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';

const DrilldownModal = ({ open, onClose, data }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  if (!data) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth fullScreen={isMobile}>
      <DialogTitle sx={{ background: theme.palette.mode === 'dark' ? '#222' : '#f5f5f5', fontSize: isMobile ? '1.1rem' : '1.25rem', p: isMobile ? 1 : 2 }}>
        Period Details
      </DialogTitle>
      <DialogContent dividers sx={{ background: theme.palette.mode === 'dark' ? '#1a1a1a' : '#fff', p: isMobile ? 1 : 2 }}>
        <List>
          {Object.entries(data).map(([key, value]) => (
            <ListItem key={key} dense sx={{ px: isMobile ? 1 : 2, py: isMobile ? 0.5 : 1 }}>
              <ListItemText
                primary={key}
                secondary={typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value)}
                primaryTypographyProps={{ fontSize: isMobile ? '0.95rem' : '1rem' }}
                secondaryTypographyProps={{ fontSize: isMobile ? '0.9rem' : '0.95rem' }}
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions sx={{ background: theme.palette.mode === 'dark' ? '#222' : '#f5f5f5', p: isMobile ? 1 : 2 }}>
        <Button onClick={onClose} color="primary" variant="contained" fullWidth={isMobile}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DrilldownModal; 