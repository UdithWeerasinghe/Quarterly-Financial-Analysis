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
import { Box } from '@mui/material';
import { formatDate } from '../../utils/dateFormat';
import { metricColors, comparisonColors } from '../../utils/colors';
import ExportBar from '../ExportBar'; // adjust path if needed
import DrilldownModal from '../DrilldownModal';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import TimeRangeSlider from '../Metrics/TimeRangeSlider';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const ComparisonChart = ({ data, metrics, isAnnual, yearRange, yearOptions, quarterRange, quarterOptions, darkMode }) => {
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
    datasets: metrics.map((metric, i) => ({
      label: metric,
      data: filteredData.map(d => d[metric]),
      borderColor: metricColors[metric] || comparisonColors[i % comparisonColors.length],
      backgroundColor: (metricColors[metric] || comparisonColors[i % comparisonColors.length]) + '33',
      borderWidth: 3,
      tension: 0.1,
      fill: true,
    })),
  };

  const axisColor = darkMode ? '#bbb' : '#333';
  const gridColor = darkMode ? '#444' : '#eee';
  const bgColor = darkMode ? '#222' : '#fff';

  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top', labels: { color: axisColor } },
      title: { display: true, text: `${metrics[0]} vs ${metrics[1]}`, color: axisColor },
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
        grid: { color: gridColor }
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
      <ExportBar chartRef={chartRef} data={filteredData} fileName={`${metrics[0]}_vs_${metrics[1]}`} />
      <Box sx={{ minWidth: isMobile ? 350 : 'auto', width: '100%' }}>
        <Line ref={chartRef} data={{
          ...chartData,
          labels: isAnnual
            ? filteredData.map(d => new Date(d.TableDate).getFullYear().toString())
            : filteredData.map((d, index) => formatDate(d.TableDate, isAnnual, index, filteredData)),
          datasets: chartData.datasets.map(ds => ({
            ...ds,
            data: filteredData.map(d => d[ds.label]),
          })),
        }} options={options} onClick={handleChartClick} />
      </Box>
      <DrilldownModal open={modalOpen} onClose={() => setModalOpen(false)} data={modalData} />
    </Box>
  );
};

export default ComparisonChart; 