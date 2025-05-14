// ChatInterface.js
// Provides an interactive chat interface for users to ask questions about financial data.
// Integrates with the backend LLM-powered API for natural language Q&A.
//
// Usage:
//   <ChatInterface darkMode={darkMode} />
//
// Props:
//   darkMode (bool): Whether to use dark mode styling.
import React, { useState } from 'react';
import {
  Box,
  Fab,
  Paper,
  Typography,
  TextField,
  IconButton,
  Tooltip,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import SendIcon from '@mui/icons-material/Send';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { sendChatMessage } from "../../api/chat";

const ChatInterface = ({ darkMode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleSend = async () => {
    if (!message.trim()) return;

    // Add user message to chat
    const userMessage = { role: 'user', content: message };
    setChatHistory(prev => [...prev, userMessage]);
    setMessage('');
    setIsLoading(true);

    try {
      const response = await sendChatMessage(message);
      
      if (!response) {
        throw new Error('Failed to get response from server');
      }

      setChatHistory(prev => [...prev, { role: 'assistant', content: response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${error.message}. Please try again or rephrase your question.` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Chat Button */}
      <Tooltip title="Chat" placement="left">
        <Fab
          color="primary"
          size="medium"
          onClick={() => setIsOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            zIndex: 1000,
          }}
        >
          <ChatIcon />
        </Fab>
      </Tooltip>

      {/* Chat Window */}
      {isOpen && (
        <Paper
          elevation={3}
          sx={{
            position: 'fixed',
            bottom: 80,
            right: 20,
            width: isExpanded ? '400px' : '300px',
            height: isExpanded ? '600px' : '400px',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: darkMode ? '#1a1a1a' : '#fff',
            transition: 'all 0.3s ease',
          }}
        >
          {/* Chat Header */}
          <Box
            sx={{
              p: 1,
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: darkMode ? '#2d2d2d' : '#f5f5f5',
            }}
          >
            <Typography variant="subtitle1" sx={{ ml: 1 }}>
              Financial Data Assistant
            </Typography>
            <Box>
              <Tooltip title={isExpanded ? "Collapse" : "Expand"}>
                <IconButton size="small" onClick={() => setIsExpanded(!isExpanded)}>
                  <OpenInNewIcon />
                </IconButton>
              </Tooltip>
              <IconButton size="small" onClick={() => setIsOpen(false)}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Chat Messages */}
          <Box
            sx={{
              flex: 1,
              overflow: 'auto',
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
            }}
          >
            {chatHistory.map((msg, index) => (
              <Box
                key={index}
                sx={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                }}
              >
                <Paper
                  elevation={1}
                  sx={{
                    p: 1,
                    backgroundColor: msg.role === 'user' 
                      ? (darkMode ? '#1976d2' : '#e3f2fd')
                      : (darkMode ? '#2d2d2d' : '#f5f5f5'),
                    color: msg.role === 'user' && !darkMode ? '#000' : 'inherit',
                  }}
                >
                  <Typography variant="body2">{msg.content}</Typography>
                </Paper>
              </Box>
            ))}
            {isLoading && (
              <Box
                sx={{
                  alignSelf: 'flex-start',
                  maxWidth: '80%',
                }}
              >
                <Paper
                  elevation={1}
                  sx={{
                    p: 1,
                    backgroundColor: darkMode ? '#2d2d2d' : '#f5f5f5',
                  }}
                >
                  <Typography variant="body2">Thinking...</Typography>
                </Paper>
              </Box>
            )}
          </Box>

          {/* Message Input */}
          <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about financial data..."
              variant="outlined"
              size="small"
              disabled={isLoading}
              sx={{
                '& .MuiOutlinedInput-root': {
                  backgroundColor: darkMode ? '#2d2d2d' : '#fff',
                },
              }}
              InputProps={{
                endAdornment: (
                  <IconButton 
                    onClick={handleSend} 
                    disabled={!message.trim() || isLoading}
                  >
                    <SendIcon />
                  </IconButton>
                ),
              }}
            />
          </Box>
        </Paper>
      )}
    </>
  );
};

export default ChatInterface; 