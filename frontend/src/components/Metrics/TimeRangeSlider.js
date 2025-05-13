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