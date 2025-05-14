// MetricsTab.js
// Dashboard tab for displaying a company's financial metrics as interactive charts and controls.
// Handles metric selection, time range, and passes data to MetricsChart.
//
// Usage:
//   <MetricsTab selectedCompany={company} selectedMetric={metric} darkMode={darkMode} />
//
// Props:
//   selectedCompany (string): The company to display metrics for.
//   selectedMetric (string): The metric to display (e.g., 'Revenue').
//   darkMode (bool): Whether to use dark mode styling.

import React, { useState, useEffect } from 'react';
import { Box, CircularProgress, FormControlLabel, Switch } from '@mui/material';
import axios from 'axios';
import MetricsChart from './MetricsChart';
import { getLastQuarterDataPerYear } from '../../utils/annualLastQuarter';
import TimeRangeSlider from './TimeRangeSlider';

const MetricsTab = ({ selectedCompany, selectedMetric, darkMode }) => {
  const [data, setData] = useState([]);
  const [isAnnual, setIsAnnual] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Get unique years from data
  const yearOptions = Array.from(new Set(data.map(d => new Date(d.TableDate).getFullYear()))).sort();
  const [yearRange, setYearRange] = useState([0, Math.max(0, yearOptions.length - 1)]);
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

  useEffect(() => {
    const fetchMetricsData = async () => {
      if (!selectedCompany || !selectedMetric) return;
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get('http://localhost:5000/api/metrics', {
          params: {
            company: selectedCompany,
            period: isAnnual ? 'annual' : 'quarterly'
          }
        });
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch metrics data');
        console.error('Error fetching metrics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetricsData();
  }, [selectedCompany, selectedMetric, isAnnual]);

  React.useEffect(() => {
    setYearRange([0, Math.max(0, yearOptions.length - 1)]);
  }, [isAnnual, yearOptions.length]);
  React.useEffect(() => {
    setQuarterRange([0, Math.max(0, quarterOptions.length - 1)]);
  }, [isAnnual, quarterOptions.length]);

  let displayData = data;
  if (isAnnual) {
    displayData = getLastQuarterDataPerYear(data);
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ color: 'error.main', mt: 2 }}>
        {error}
      </Box>
    );
  }

  if (!selectedCompany) {
    return (
      <Box sx={{ mt: 2 }}>
        Please select a company to view metrics
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 2 }}>
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
      <MetricsChart
        data={displayData}
        metric={selectedMetric}
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

export default MetricsTab; 