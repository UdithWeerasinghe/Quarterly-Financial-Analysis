import React, { useState } from 'react';
import { Box, Button, Menu, MenuItem } from '@mui/material';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import Papa from 'papaparse';
import jsPDF from 'jspdf';

const ExportBar = ({ chartRef, data, fileName = 'chart' }) => {
  const [anchorEl, setAnchorEl] = useState(null);

  const handleExportCSV = () => {
    const csv = Papa.unparse(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${fileName}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setAnchorEl(null);
  };

  const handleExportPNG = () => {
    if (chartRef && chartRef.current) {
      const url = chartRef.current.toBase64Image();
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${fileName}.png`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
    setAnchorEl(null);
  };

  const handleExportPDF = () => {
    if (chartRef && chartRef.current) {
      const url = chartRef.current.toBase64Image();
      const pdf = new jsPDF();
      pdf.addImage(url, 'PNG', 10, 10, 180, 90);
      pdf.save(`${fileName}.pdf`);
    }
    setAnchorEl(null);
  };

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
      <Button
        variant="outlined"
        endIcon={<ArrowDropDownIcon />}
        onClick={handleClick}
        size="small"
      >
        Export
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem onClick={handleExportCSV}>Export as CSV</MenuItem>
        <MenuItem onClick={handleExportPNG}>Export as PNG</MenuItem>
        <MenuItem onClick={handleExportPDF}>Export as PDF</MenuItem>
      </Menu>
    </Box>
  );
};

export default ExportBar;
