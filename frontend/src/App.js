// App.js
// Main entry point for the Quarterly Financial Analysis Dashboard frontend.
// Handles routing, layout, and global state for the React application.
//
// Features:
// - Renders the main dashboard layout and navigation
// - Integrates all major components (metrics, chat, comparisons, etc.)
// - Handles global state and API error boundaries
//
// Usage:
//   Place this file at the root of your src/ directory in a React app created with Create React App or Vite.

import React, { useState, useEffect } from 'react';
import { Container, Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import Header from './components/Layout/Header';
import Navigation from './components/Layout/Navigation';
import MetricsTab from './components/Metrics/MetricsTab';
import ComparisonTab from './components/Comparisons/ComparisonTab';
import RatioTab from './components/Ratios/RatioTab';
import ChatInterface from './components/Chat/ChatInterface';
import axios from 'axios';

/**
 * App
 * Main React component for the dashboard. Handles routing and layout.
 */
function App() {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [mainTab, setMainTab] = useState('metrics');
  const [subTab, setSubTab] = useState('Revenue');
  const [darkMode, setDarkMode] = useState(false);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
    },
  });

  useEffect(() => {
    // Fetch companies from the backend
    const fetchCompanies = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/companies');
        setCompanies(response.data);
      } catch (error) {
        console.error('Error fetching companies:', error);
      }
    };

    fetchCompanies();
  }, []);

  const renderContent = () => {
    if (!selectedCompany) {
      return (
        <Box sx={{ mt: 2 }}>
          Please select a company to view data
        </Box>
      );
    }

    switch (mainTab) {
      case 'metrics':
        return <MetricsTab selectedCompany={selectedCompany} selectedMetric={subTab} darkMode={darkMode} />;
      case 'comparisons':
        return <ComparisonTab selectedCompany={selectedCompany} darkMode={darkMode} />;
      case 'ratios':
        return <RatioTab selectedCompany={selectedCompany} darkMode={darkMode} />;
      default:
        return null;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header
          companies={companies}
          selectedCompany={selectedCompany}
          onCompanyChange={setSelectedCompany}
          darkMode={darkMode}
          onToggleDarkMode={() => setDarkMode((prev) => !prev)}
        />
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flex: 1 }}>
          <Navigation
            mainTab={mainTab}
            subTab={subTab}
            onMainTabChange={setMainTab}
            onSubTabChange={setSubTab}
          />
          {renderContent()}
        </Container>
        <ChatInterface darkMode={darkMode} />
      </Box>
    </ThemeProvider>
  );
}

export default App;