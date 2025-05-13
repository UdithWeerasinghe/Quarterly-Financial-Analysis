import React, { useState, useEffect } from 'react';
import { Box, CircularProgress, Tabs, Tab, FormControlLabel, Switch } from '@mui/material';
import ComparisonChart from './ComparisonChart';
import axios from 'axios';
import TimeRangeSlider from '../Metrics/TimeRangeSlider';
import { getQuarterLabel } from '../../utils/dateFormat';

const comparisonPairs = [
  { label: 'Revenue vs. Cost of Goods Sold (COGS)', metrics: ['Revenue', 'COGS'] },
  { label: 'Revenue vs. Gross Profit', metrics: ['Revenue', 'Gross Profit'] },
  { label: 'Gross Profit vs. Operating Expenses', metrics: ['Gross Profit', 'Operating Expenses'] },
  { label: 'Operating Income vs. Operating Expenses', metrics: ['Operating Income', 'Operating Expenses'] },
  { label: 'Operating Income vs. Net Income', metrics: ['Operating Income', 'Net Income'] },
  { label: 'Revenue vs. Net Income', metrics: ['Revenue', 'Net Income'] },
];

const ComparisonTab = ({ selectedCompany, darkMode }) => {
  const [data, setData] = useState([]);
  const [isAnnual, setIsAnnual] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [subTab, setSubTab] = useState(0);
  const yearOptions = Array.from(new Set(data.map(d => new Date(d.TableDate).getFullYear()))).sort();
  const [yearRange, setYearRange] = useState([0, Math.max(0, yearOptions.length - 1)]);
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
    const fetchData = async () => {
      if (!selectedCompany) return;
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get('http://localhost:5000/api/comparisons', {
          params: {
            company: selectedCompany,
            period: isAnnual ? 'annual' : 'quarterly'
          }
        });
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch comparison data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedCompany, isAnnual]);

  React.useEffect(() => {
    setYearRange([0, Math.max(0, yearOptions.length - 1)]);
  }, [isAnnual, yearOptions.length]);

  React.useEffect(() => {
    setQuarterRange([0, Math.max(0, quarterOptions.length - 1)]);
  }, [isAnnual, quarterOptions.length]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
  if (error) return <Box sx={{ color: 'error.main', mt: 2 }}>{error}</Box>;
  if (!selectedCompany) return <Box sx={{ mt: 2 }}>Please select a company to view comparisons</Box>;

  return (
    <Box sx={{ mt: 2 }}>
      <Tabs
        value={subTab}
        onChange={(_, v) => setSubTab(v)}
        sx={{ mb: 2 }}
        variant="scrollable"
        scrollButtons="auto"
      >
        {comparisonPairs.map((pair, idx) => (
          <Tab key={pair.label} label={pair.label} value={idx} />
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
      <ComparisonChart
        data={data}
        metrics={comparisonPairs[subTab].metrics}
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

export default ComparisonTab; 