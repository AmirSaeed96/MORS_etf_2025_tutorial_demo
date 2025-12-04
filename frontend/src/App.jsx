import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

// Generate UUID for conversation
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

function App() {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState(() => generateUUID())
  const [routingMode, setRoutingMode] = useState('auto')
  const [health, setHealth] = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Check health on mount
  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/health')
      const data = await response.json()
      setHealth(data)
    } catch (error) {
      console.error('Health check failed:', error)
      setHealth({ status: 'error' })
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: inputValue,
          override_routing: routingMode
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      const assistantMessage = {
        role: 'assistant',
        content: data.message.content,
        metadata: data.message.metadata,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message}. Please check that the backend is running on http://localhost:8000`,
        metadata: { error: true },
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const startNewConversation = () => {
    const newId = generateUUID()
    setConversationId(newId)
    setMessages([])
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <h1>Quantum Wiki RAG</h1>
            <span className="subtitle">Phoenix Observability Demo</span>
          </div>
          <div className="header-right">
            {health && (
              <div className={`health-indicator ${health.status}`}>
                <span className="health-dot"></span>
                {health.status}
              </div>
            )}
            <a
              href="http://localhost:6006"
              target="_blank"
              rel="noopener noreferrer"
              className="phoenix-link"
            >
              Open Phoenix UI →
            </a>
          </div>
        </div>
      </header>

      {/* Controls */}
      <div className="controls">
        <div className="routing-controls">
          <label>Routing Mode:</label>
          <select
            value={routingMode}
            onChange={(e) => setRoutingMode(e.target.value)}
            className="routing-select"
          >
            <option value="auto">Auto (Intelligent Routing)</option>
            <option value="rag">Always RAG</option>
            <option value="no_rag">Never RAG</option>
          </select>
        </div>
        <button onClick={startNewConversation} className="new-conversation-btn">
          New Conversation
        </button>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to Quantum Wiki RAG!</h2>
            <p>Ask me anything about quantum physics. I'll search Wikipedia articles to help answer your questions.</p>
            <div className="example-questions">
              <p><strong>Try asking:</strong></p>
              <ul>
                <li>"What is quantum entanglement?"</li>
                <li>"Explain the uncertainty principle"</li>
                <li>"How does quantum computing work?"</li>
              </ul>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-header">
              <strong>{msg.role === 'user' ? 'You' : 'Assistant'}</strong>
              {msg.metadata && (
                <div className="message-badges">
                  {msg.metadata.used_rag !== undefined && (
                    <span className={`badge ${msg.metadata.used_rag ? 'rag-yes' : 'rag-no'}`}>
                      RAG: {msg.metadata.used_rag ? 'Used' : 'Not Used'}
                    </span>
                  )}
                  {msg.metadata.review_label && (
                    <span className={`badge review-${msg.metadata.review_label}`}>
                      Review: {msg.metadata.review_label}
                    </span>
                  )}
                  {msg.metadata.trace_id && (
                    <span className="badge trace-id" title={msg.metadata.trace_id}>
                      Trace: {msg.metadata.trace_id.substring(0, 8)}...
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="message-content">
              {msg.role === 'assistant' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="message-header">
              <strong>Assistant</strong>
            </div>
            <div className="message-content loading">
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              Processing through agents...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-container">
        <textarea
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question about quantum physics..."
          className="message-input"
          rows="3"
          disabled={isLoading}
        />
        <button
          onClick={sendMessage}
          disabled={isLoading || !inputValue.trim()}
          className="send-button"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default App
