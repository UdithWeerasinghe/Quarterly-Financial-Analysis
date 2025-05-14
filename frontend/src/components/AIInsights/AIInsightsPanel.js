// AIInsightsPanel.js
// Provides AI-generated insights, summaries, or anomaly detection for financial data visualizations.
// Integrates with the backend or local models to generate context-aware insights for the dashboard.
//
// Usage:
//   <AIInsightsPanel data={data} metric={metric} isAnnual={isAnnual} darkMode={darkMode} />
//
// Props:
//   data (array): Array of financial data objects for the selected metric.
//   metric (string): The metric being visualized.
//   isAnnual (bool): Whether the data is annualized.
//   darkMode (bool): Whether to use dark mode styling.

import React from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Paper } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';

const AIInsightsPanel = ({ data, metric, isAnnual, darkMode }) => {
  const generateInsights = (data, metric, isAnnual) => {
    const insights = [];
    const validData = data.filter(d => d.TableDate && !isNaN(new Date(d.TableDate).getTime()));
    
    if (validData.length < 2) return insights;

    // Calculate basic statistics
    const values = validData.map(d => d[metric]);
    const latestValue = values[values.length - 1];
    const previousValue = values[values.length - 2];
    const percentChange = ((latestValue - previousValue) / previousValue) * 100;
    
    // Calculate trend using simple moving average
    const recentValues = values.slice(-4);
    const trend = recentValues.reduce((sum, val, idx, arr) => {
      if (idx === 0) return 0;
      return sum + (val - arr[idx - 1]);
    }, 0) / (recentValues.length - 1);

    // Generate insights based on the data
    if (percentChange > 20) {
      insights.push({
        type: 'positive',
        text: `Strong growth: ${metric} increased by ${percentChange.toFixed(1)}% in the latest period`
      });
    } else if (percentChange < -20) {
      insights.push({
        type: 'negative',
        text: `Significant decline: ${metric} decreased by ${Math.abs(percentChange).toFixed(1)}% in the latest period`
      });
    }

    if (trend > 0) {
      insights.push({
        type: 'positive',
        text: `Upward trend: ${metric} shows consistent growth over the last 4 periods`
      });
    } else if (trend < 0) {
      insights.push({
        type: 'negative',
        text: `Downward trend: ${metric} shows consistent decline over the last 4 periods`
      });
    }

    // Simple volatility check
    const maxValue = Math.max(...recentValues);
    const minValue = Math.min(...recentValues);
    const avgValue = recentValues.reduce((a, b) => a + b, 0) / recentValues.length;
    const volatility = (maxValue - minValue) / avgValue;

    if (volatility > 0.3) {
      insights.push({
        type: 'warning',
        text: `High volatility: ${metric} shows significant fluctuations in recent periods`
      });
    }

    // Annual growth analysis
    if (isAnnual) {
      const yearlyGrowth = values.slice(-4).reduce((acc, val, idx, arr) => {
        if (idx === 0) return acc;
        return acc + ((val - arr[idx - 1]) / arr[idx - 1]);
      }, 0) / 3;
      
      if (yearlyGrowth > 0.1) {
        insights.push({
          type: 'info',
          text: `Strong annual growth: ${metric} has grown by ${(yearlyGrowth * 100).toFixed(1)}% annually on average`
        });
      }
    }

    // Add contextual insights based on metric type
    if (metric.toLowerCase().includes('revenue')) {
      if (percentChange > 0) {
        insights.push({
          type: 'info',
          text: 'Revenue growth indicates strong market demand and business expansion'
        });
      }
    } else if (metric.toLowerCase().includes('profit')) {
      if (percentChange > 0) {
        insights.push({
          type: 'info',
          text: 'Profit growth suggests improved operational efficiency and cost management'
        });
      }
    } else if (metric.toLowerCase().includes('margin')) {
      if (percentChange > 0) {
        insights.push({
          type: 'info',
          text: 'Margin improvement indicates better pricing power and cost control'
        });
      }
    }

    return insights;
  };

  const insights = generateInsights(data, metric, isAnnual);

  const getIcon = (type) => {
    switch (type) {
      case 'positive':
        return <TrendingUpIcon color="success" />;
      case 'negative':
        return <TrendingDownIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'info':
        return <InfoIcon color="info" />;
      default:
        return <InfoIcon />;
    }
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        mt: 2, 
        p: 2, 
        backgroundColor: darkMode ? '#1a1a1a' : '#fff',
        color: darkMode ? '#fff' : 'inherit'
      }}
    >
      <Typography variant="h6" gutterBottom>
        AI Insights
      </Typography>
      <List>
        {insights.map((insight, index) => (
          <ListItem key={index}>
            <ListItemIcon>
              {getIcon(insight.type)}
            </ListItemIcon>
            <ListItemText primary={insight.text} />
          </ListItem>
        ))}
        {insights.length === 0 && (
          <ListItem>
            <ListItemIcon>
              <InfoIcon />
            </ListItemIcon>
            <ListItemText primary="No significant insights available for this metric" />
          </ListItem>
        )}
      </List>
    </Paper>
  );
};

export default AIInsightsPanel; 