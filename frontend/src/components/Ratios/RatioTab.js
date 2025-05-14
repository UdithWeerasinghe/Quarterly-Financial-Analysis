// RatioTab.js
// Dashboard tab for displaying a company's financial ratios as interactive charts and controls.
// Handles ratio selection, time range, and passes data to RatioChart.
//
// Usage:
//   <RatioTab selectedCompany={company} darkMode={darkMode} />
//
// Props:
//   selectedCompany (string): The company to display ratios for.
//   darkMode (bool): Whether to use dark mode styling.

import React, { useState, useEffect } from 'react';
import { Box, CircularProgress, Tabs, Tab, FormControlLabel, Switch } from '@mui/material';
import RatioChart from './RatioChart';
import axios from 'axios';
import TimeRangeSlider from '../Metrics/TimeRangeSlider';

const ratioOptions = [
  { label: 'Gross Margin (%)', key: 'Gross Margin' },
  { label: 'Operating Margin (%)', key: 'Operating Margin' },
  { label: 'Net Margin (%)', key: 'Net Margin' },
];

const RatioTab = ({ selectedCompany, darkMode }) => {
  const [data, setData] = useState([]);
  const [isAnnual, setIsAnnual] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [subTab, setSubTab] = useState(0);
  // Get unique years from data
  const yearOptions = Array.from(new Set(data.map(d => new Date(d.TableDate).getFullYear()))).sort();
  const [yearRange, setYearRange] = useState([0, yearOptions.length - 1]);
  // Quarters: generate sorted list of all quarters in the data
  const quarterOptions = data
    .map(d => {
      const date = new Date(d.TableDate);
      const year = date.getFullYear();
      const q = Math.floor(date.getMonth() / 3) + 1;
      return `${year} Q${q}`;
    })
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .sort();
  const [quarterRange, setQuarterRange] = useState([0, Math.max(0, quarterOptions.length - 1)]);
  React.useEffect(() => {
    setYearRange([0, yearOptions.length - 1]);
    setQuarterRange([0, Math.max(0, quarterOptions.length - 1)]);
  }, [isAnnual, yearOptions.length, quarterOptions.length]);

  useEffect(() => {
    const fetchData = async () => {
      if (!selectedCompany) return;
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get('http://localhost:5000/api/ratios', {
          params: {
            company: selectedCompany,
            period: isAnnual ? 'annual' : 'quarterly'
          }
        });
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch ratio data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedCompany, isAnnual]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
  if (error) return <Box sx={{ color: 'error.main', mt: 2 }}>{error}</Box>;
  if (!selectedCompany) return <Box sx={{ mt: 2 }}>Please select a company to view ratios</Box>;

  return (
    <Box sx={{ mt: 2 }}>
      <Tabs value={subTab} onChange={(_, v) => setSubTab(v)} sx={{ mb: 2 }}>
        {ratioOptions.map((ratio, idx) => (
          <Tab key={ratio.label} label={ratio.label} value={idx} />
        ))}
      </Tabs>
      <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', mb: 1 }}>
        <FormControlLabel
          control={
            <Switch
              checked={isAnnual}
              onChange={e => setIsAnnual(e.target.checked)}
            />
          }
          label="Annual View"
        />
        {isAnnual && yearOptions.length > 1 && (
          <TimeRangeSlider
            options={yearOptions.map(String)}
            value={yearRange}
            onChange={setYearRange}
          />
        )}
        {!isAnnual && quarterOptions.length > 1 && (
          <TimeRangeSlider
            options={quarterOptions}
            value={quarterRange}
            onChange={setQuarterRange}
          />
        )}
      </Box>
      <RatioChart
        data={data}
        ratio={ratioOptions[subTab].key}
        isAnnual={isAnnual}
        yearRange={yearRange}
        yearOptions={yearOptions}
        quarterRange={quarterRange}
        quarterOptions={quarterOptions}
        darkMode={darkMode}
      />
    </Box>
  );
};

export default RatioTab; 