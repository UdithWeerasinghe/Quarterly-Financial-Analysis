// MetricsChart.js
// Renders a time series chart for a selected financial metric of a company.
// Supports dynamic time range selection, responsive design, and export options.
//
// Usage:
//   <MetricsChart data={data} metric={selectedMetric} company={selectedCompany} onDrilldown={handleDrilldown} />
//
// Props:
//   data (array): Array of financial data objects for the selected company.
//   metric (string): The financial metric to plot (e.g., 'Revenue').
//   company (string): The company name or code.
//   onDrilldown (function): Callback for when a data point is clicked for drilldown.

import React, { useRef, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Box} from '@mui/material';
import { formatDate } from '../../utils/dateFormat';
import { metricColors } from '../../utils/colors';
import ExportBar from '../ExportBar'; // adjust path as needed
import DrilldownModal from '../DrilldownModal'; // adjust path as needed
import annotationPlugin from 'chartjs-plugin-annotation';
import { Chart } from 'chart.js';
import AIInsightsPanel from '../AIInsights/AIInsightsPanel';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';


// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

Chart.register(annotationPlugin);

const detectAnomalies = (data, metric, threshold = 2) => {
  const anomalies = [];
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1][metric];
    const curr = data[i][metric];
    if (prev && curr) {
      const ratio = curr / prev;
      const date = new Date(data[i].TableDate).toISOString().split('T')[0]; // Format date without time
      if (ratio > threshold) {
        anomalies.push({
          index: i,
          type: 'spike',
          message: `Spike: ${metric} increased by ${(ratio * 100 - 100).toFixed(1)}% on ${date}`
        });
      } else if (ratio < 1 / threshold) {
        anomalies.push({
          index: i,
          type: 'drop',
          message: `Drop: ${metric} decreased by ${(100 - ratio * 100).toFixed(1)}% on ${date}`
        });
      }
    }
  }
  return anomalies;
};

const MetricsChart = ({
  data,
  metric,
  isAnnual,
  yearRange,
  yearOptions,
  quarterRange,
  quarterOptions,
  darkMode
}) => {
  const chartRef = useRef(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalData, setModalData] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Filter out data points with invalid TableDate
  const validData = data.filter(d => {
    const date = new Date(d.TableDate);
    return d.TableDate && !isNaN(date.getTime());
  });

  // Filter data for annual or quarterly view
  let filteredData = validData;
  if (
    isAnnual &&
    Array.isArray(yearOptions) &&
    yearOptions.length > 0 &&
    Array.isArray(yearRange) &&
    yearRange.length === 2
  ) {
    const [startIdx, endIdx] = yearRange;
    const selectedYears = yearOptions.slice(startIdx, endIdx + 1);
    filteredData = validData.filter(d => selectedYears.includes(new Date(d.TableDate).getFullYear()));
  } else if (
    !isAnnual &&
    Array.isArray(quarterOptions) &&
    quarterOptions.length > 0 &&
    Array.isArray(quarterRange) &&
    quarterRange.length === 2
  ) {
    const [startIdx, endIdx] = quarterRange;
    const selectedQuarters = quarterOptions.slice(startIdx, endIdx + 1);
    filteredData = validData.filter(d => {
      const date = new Date(d.TableDate);
      const year = date.getFullYear();
      const q = Math.floor(date.getMonth() / 3) + 1;
      return selectedQuarters.includes(`${year} Q${q}`);
    });
  }

  const chartData = {
    labels: isAnnual
      ? filteredData.map(d => new Date(d.TableDate).getFullYear().toString())
      : filteredData.map((d, index) => formatDate(d.TableDate, isAnnual, index, filteredData)),
    datasets: [
      {
        label: metric,
        data: filteredData.map(d => d[metric]),
        borderColor: metricColors[metric] || '#1976d2',
        backgroundColor: (metricColors[metric] || '#1976d2') + '33',
        tension: 0.1,
        fill: true,
      },
    ],
  };

  const axisColor = darkMode ? '#bbb' : '#333';
  const gridColor = darkMode ? '#444' : '#eee';
  const bgColor = darkMode ? '#222' : '#fff';

  const anomalies = detectAnomalies(filteredData, metric);
  // Create a map of anomalies for quick lookup
  const anomalyMap = anomalies.reduce((acc, anomaly) => {
    acc[anomaly.index] = anomaly;
    return acc;
  }, {});

  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top', labels: { color: axisColor } },
      title: {
        display: true,
        text: `${metric} Over Time`,
        font: {
          size: 16
        }
      },
      tooltip: {
        enabled: true,
        backgroundColor: bgColor,
        titleColor: axisColor,
        bodyColor: axisColor,
        borderColor: gridColor,
        borderWidth: 1,
        callbacks: {
          title: function(context) {
            // Show the date/period as the title
            const idx = context[0].dataIndex;
            const label = context[0].chart.data.labels[idx];
            return label;
          },
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) label += ': ';
            let value = context.parsed.y;
            // Format as percent if label includes 'margin'
            if (label.toLowerCase().includes('margin')) {
              value = value?.toLocaleString(undefined, { maximumFractionDigits: 2 }) + '%';
            } else if (label.toLowerCase().includes('revenue') || label.toLowerCase().includes('income') || label.toLowerCase().includes('profit')) {
              value = 'LKR ' + value?.toLocaleString(undefined, { maximumFractionDigits: 2 });
            } else {
              value = value?.toLocaleString(undefined, { maximumFractionDigits: 2 });
            }
            // Optionally, show change from previous point
            const idx = context.dataIndex;
            const dataArr = context.dataset.data;
            if (idx > 0) {
              const prev = dataArr[idx - 1];
              if (prev !== undefined && prev !== null) {
                const diff = value - prev;
                const pct = prev !== 0 ? (diff / prev) * 100 : 0;
                value += ` (${diff >= 0 ? '+' : ''}${diff.toLocaleString(undefined, { maximumFractionDigits: 2 })}, ${pct >= 0 ? '+' : ''}${pct.toLocaleString(undefined, { maximumFractionDigits: 2 })}%)`;
              }
            }
            return label + value;
          },
          afterBody: function(context) {
            const idx = context[0].dataIndex;
            const anomaly = anomalyMap[idx];
            if (anomaly) {
              return [
                '',
                anomaly.message
              ];
            }
            return [];
          }
        }
      }
    },
    scales: {
      x: {
        ticks: { color: axisColor, autoSkip: false, maxRotation: 45, minRotation: 45 },
        grid: { color: gridColor }
      },
      y: {
        beginAtZero: true,
        ticks: { color: axisColor },
        grid: { color: gridColor },
        title: {
          display: true,
          text: "Rs. '000",
          font: {
            size: 14
          }
        }
      },
    },
  };

  const handleChartClick = (event) => {
    if (!chartRef.current) return;
    const chart = chartRef.current;
    const points = chart.getElementsAtEventForMode(event.nativeEvent, 'nearest', { intersect: true }, true);
    if (points.length) {
      const idx = points[0].index;
      setModalData(filteredData[idx]);
      setModalOpen(true);
    }
  };

  return (
    <Box sx={{ mt: 2, px: isMobile ? 0.5 : 2, width: '100%', overflowX: isMobile ? 'auto' : 'visible' }}>
      <ExportBar chartRef={chartRef} data={filteredData} fileName={metric} />
      <Box sx={{ minWidth: isMobile ? 350 : 'auto', width: '100%' }}>
        <Line ref={chartRef} data={{
          ...chartData,
          labels: isAnnual
            ? filteredData.map(d => new Date(d.TableDate).getFullYear().toString())
            : filteredData.map((d, index) => formatDate(d.TableDate, isAnnual, index, filteredData)),
          datasets: [
            {
              ...chartData.datasets[0],
              data: filteredData.map(d => d[metric]),
            },
          ],
        }} options={options} onClick={handleChartClick} />
      </Box>
      <DrilldownModal open={modalOpen} onClose={() => setModalOpen(false)} data={modalData} />
      <AIInsightsPanel data={filteredData} metric={metric} isAnnual={isAnnual} darkMode={darkMode} />
    </Box>
  );
};

export default MetricsChart; 