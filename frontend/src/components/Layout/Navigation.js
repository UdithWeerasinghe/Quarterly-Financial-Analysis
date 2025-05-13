import React, { useEffect } from 'react';
import { Tabs, Tab, Box, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';

const Navigation = ({ mainTab, subTab, onMainTabChange, onSubTabChange }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const getSubTabs = (mainTab) => {
    switch (mainTab) {
      case 'metrics':
        return ['Revenue', 'COGS', 'Gross Profit', 'Operating Expenses', 'Operating Income', 'Net Income'];
      case 'comparisons':
        return ['Revenue vs COGS', 'Revenue vs Gross Profit', 'Gross Profit vs Operating Expenses', 
                'Operating Income vs Operating Expenses', 'Operating Income vs. Net Income', 'Revenue vs. Net Income'];
      case 'ratios':
        return ['Gross Margin(%)', 'Operating Margin(%)', 'Net Margin(%)'];
      default:
        return [];
    }
  };

  // Set first sub-tab when main tab changes
  useEffect(() => {
    const subTabs = getSubTabs(mainTab);
    if (subTabs.length > 0 && !subTabs.includes(subTab)) {
      onSubTabChange(subTabs[0]);
    }
  }, [mainTab]);

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
      <Tabs
        value={mainTab}
        onChange={(e, newValue) => onMainTabChange(newValue)}
        variant={isMobile ? 'scrollable' : 'standard'}
        scrollButtons={isMobile ? 'auto' : false}
        textColor="primary"
        indicatorColor="primary"
        sx={{
          minHeight: isMobile ? 36 : 48,
          '& .MuiTab-root': {
            fontSize: isMobile ? '0.95rem' : '1.1rem',
            minHeight: isMobile ? 36 : 48,
          },
        }}
      >
        <Tab label="Metrics" value="metrics" />
        <Tab label="Comparisons" value="comparisons" />
        <Tab label="Margin Ratios" value="ratios" />
      </Tabs>
      {mainTab === 'metrics' && (
        <Tabs
          value={subTab}
          onChange={(e, newValue) => onSubTabChange(newValue)}
          variant={isMobile ? 'scrollable' : 'standard'}
          scrollButtons={isMobile ? 'auto' : false}
          textColor="primary"
          indicatorColor="primary"
          sx={{
            minHeight: isMobile ? 32 : 44,
            '& .MuiTab-root': {
              fontSize: isMobile ? '0.9rem' : '1rem',
              minHeight: isMobile ? 32 : 44,
            },
          }}
        >
          {getSubTabs(mainTab).map((tab) => (
            <Tab key={tab} label={tab} value={tab} />
          ))}
        </Tabs>
      )}
    </Box>
  );
};

export default Navigation; 