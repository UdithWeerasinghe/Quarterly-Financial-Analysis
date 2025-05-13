import React from 'react';
import { AppBar, Toolbar, Typography, Select, MenuItem, Box, IconButton, Tooltip } from '@mui/material';

const companyNames = {
  'DIPD': 'DIPPED PRODUCTS PLC',
  'REXP': 'RICHARD PIERIS EXPORTS PLC'
};

const companyOptions = [
  { value: 'DIPD', label: 'DIPPED PRODUCTS PLC', logo: '/logos/dipd.jpeg' },
  { value: 'REXP', label: 'RICHARD PIERIS EXPORTS PLC', logo: '/logos/rexp.jpeg' },
];

const Header = ({ companies, selectedCompany, onCompanyChange, darkMode, onToggleDarkMode }) => {
  return (
    <AppBar position="static">
      <Toolbar>
        <img src="/logos/cse.png" alt="CSE Logo" style={{ height: 56, marginRight: 20 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Quarterly Financial Analysis
        </Typography>
        <Box sx={{ minWidth: 200 }}>
        <Select
            value={selectedCompany || ''}
            onChange={(e) => onCompanyChange(e.target.value)}
            displayEmpty
            fullWidth
            sx={{ backgroundColor: 'white', color: 'black' }}
            renderValue={selected => {
              if (!selected) return 'Select Company';
              const option = companyOptions.find(opt => opt.value === selected);
              if (!option) return 'Select Company';
              return (
                <Box display="flex" alignItems="center">
                  <img src={option.logo} alt={option.label} style={{ height: 24, marginRight: 8, borderRadius: 4 }} />
                  {option.label}
                </Box>
              );
            }}
          >
            <MenuItem value="" disabled>
              Select Company
            </MenuItem>
            {companyOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                <img
                  src={option.logo}
                  alt={option.label}
                  style={{ height: 24, marginRight: 8, verticalAlign: 'middle', borderRadius: 4 }}
                />
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <Tooltip title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}>
          <IconButton sx={{ ml: 2 }} onClick={onToggleDarkMode} color="inherit">
            {darkMode ? '☀️' : '🌙'}
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  );
};

export default Header; 