// TimeRangeSlider.js
// Slider component for selecting a range of years or quarters for chart filtering.
// Used in the metrics dashboard to allow users to zoom in on a specific time period.
//
// Usage:
//   <TimeRangeSlider options={options} value={range} onChange={setRange} />
//
// Props:
//   options (array): List of string labels for the slider (e.g., years or quarters).
//   value (array): [startIndex, endIndex] for the selected range.
//   onChange (function): Callback to update the selected range.

import React from 'react';
import { Box, Slider } from '@mui/material';

const TimeRangeSlider = ({ options, value, onChange }) => {
  // value: [startIdx, endIdx]
  const min = 0;
  const max = options.length - 1;

  const handleChange = (event, newValue) => {
    onChange(newValue);
  };

  return (
    <Box sx={{ minWidth: 200, px: 2 }}>
      <Slider
        value={value}
        min={min}
        max={max}
        onChange={handleChange}
        valueLabelDisplay="off"
        marks={options.map((opt, idx) => ({ value: idx, label: idx === value[0] || idx === value[1] ? opt : '' }))}
        step={1}
        disableSwap
      />
    </Box>
  );
};

export default TimeRangeSlider; 