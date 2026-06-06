import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Head from 'next/head';
import ReactMarkdown from 'react-markdown';

// Updated for Vercel deployment compatibility - v2.0

interface Source {
  index: number;
  play: string;
  act: string;
  scene_title: string;
  similarity: number;
}

interface AnswerResponse {
  answer: string;
  sources: Source[];
}

interface Play {
  title: string;
  category: string;
}

export default function Home() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedPlay, setSelectedPlay] = useState<Play | null>(null);
  const [showTragediesOnly, setShowTragediesOnly] = useState(false);
  const [activeTab, setActiveTab] = useState<'short' | 'detailed'>('short');

  const backendUrl = 'https://web-production-9f2fc.up.railway.app';

  // Shakespeare plays data
  const plays: Play[] = [
    { title: "All's Well That Ends Well", category: "Comedy" },
    { title: "Antony and Cleopatra", category: "Tragedy" },
    { title: "As You Like It", category: "Comedy" },
    { title: "The Comedy of Errors", category: "Comedy" },
    { title: "Coriolanus", category: "Tragedy" },
    { title: "Cymbeline", category: "Tragedy" },
    { title: "Hamlet", category: "Tragedy" },
    { title: "Henry IV, Part 1", category: "History" },
    { title: "Henry IV, Part 2", category: "History" },
    { title: "Henry V", category: "History" },
    { title: "Henry VI, Part 1", category: "History" },
    { title: "Henry VI, Part 2", category: "History" },
    { title: "Henry VI, Part 3", category: "History" },
    { title: "Henry VIII", category: "History" },
    { title: "Julius Caesar", category: "Tragedy" },
    { title: "King John", category: "History" },
    { title: "King Lear", category: "Tragedy" },
    { title: "Love's Labour's Lost", category: "Comedy" },
    { title: "Macbeth", category: "Tragedy" },
    { title: "Measure for Measure", category: "Comedy" },
    { title: "The Merchant of Venice", category: "Comedy" },
    { title: "The Merry Wives of Windsor", category: "Comedy" },
    { title: "A Midsummer Night's Dream", category: "Comedy" },
    { title: "Much Ado About Nothing", category: "Comedy" },
    { title: "Othello", category: "Tragedy" },
    { title: "Pericles, Prince of Tyre", category: "Tragedy" },
    { title: "Richard II", category: "History" },
    { title: "Richard III", category: "History" },
    { title: "Romeo and Juliet", category: "Tragedy" },
    { title: "The Taming of the Shrew", category: "Comedy" },
    { title: "The Tempest", category: "Comedy" },
    { title: "Timon of Athens", category: "Tragedy" },
    { title: "Titus Andronicus", category: "Tragedy" },
    { title: "Troilus and Cressida", category: "Tragedy" },
    { title: "Twelfth Night", category: "Comedy" },
    { title: "The Two Gentlemen of Verona", category: "Comedy" },
    { title: "The Two Noble Kinsmen", category: "Tragedy" },
    { title: "The Winter's Tale", category: "Comedy" }
  ];

  const filteredPlays = showTragediesOnly 
    ? plays.filter(play => play.category === 'Tragedy')
    : plays;

  const askQuestion = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    setAnswer('');
    setSources([]);

    try {
      const requestPayload: any = {
        question: question,
        k: 5 // Request 5 chunks for better context
      };

      // Add play filter if a play is selected
      if (selectedPlay) {
        requestPayload.filters = {
          play: selectedPlay.title
        };
      }

      const response = await axios.post(`${backendUrl}/answer`, requestPayload);
      const data: AnswerResponse = response.data;
      setAnswer(data.answer);
      setSources(data.sources);
    } catch (err: any) {
      console.error('API Error:', err);
      if (err.response) {
        // Server responded with error status
        setError(`Server Error: ${err.response.data?.detail || err.response.statusText}`);
      } else if (err.request) {
        // Network error
        setError('Network Error: Unable to connect to the server. Please check your internet connection.');
      } else {
        // Other error
        setError(`Error: ${err.message || 'An unexpected error occurred.'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const selectPlay = (play: Play) => {
    setSelectedPlay(play);
  };

  // Function to format quotes with proper indentation
  const formatAnswer = (text: string) => {
    // Split the text into paragraphs
    const paragraphs = text.split('\n\n');
    
    return paragraphs.map((paragraph, index) => {
      // Check if this paragraph contains a quote (starts with quote marks)
      if (paragraph.trim().startsWith('"') || paragraph.includes('(Act') || paragraph.includes('(Scene')) {
        return (
          <div key={index} style={{
            marginLeft: '2rem',
            marginBottom: '1rem',
            fontStyle: 'italic',
            borderLeft: '3px solid #B34348',
            paddingLeft: '1rem',
            backgroundColor: '#f8f9fa',
            padding: '1rem',
            borderRadius: '4px'
          }}>
            {paragraph}
          </div>
        );
      }
      
      // Regular paragraph
      return (
        <div key={index} style={{ marginBottom: '1rem' }}>
          {paragraph}
        </div>
      );
    });
  };

  return (
    <>
      <Head>
        <title>Shakespeare GPT - Academic Dictionary Style</title>
        <meta name="description" content="Ask questions about Shakespeare and get contextual answers from his plays" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet" />
        <script src="https://cdn.tailwindcss.com"></script>
        <style dangerouslySetInnerHTML={{
          __html: `
            body {
              font-family: 'Inter, sans-serif';
              background: linear-gradient(135deg, #F5F1E8 0%, #E8E0D0 100%);
              margin: 0;
              padding: 0;
              color: #2D3748;
            }
            .serif-font {
              font-family: 'Inter, sans-serif';
            }
            .accent-color {
              color: #6B46C1;
            }
            .accent-bg {
              background-color: #6B46C1;
            }
            .accent-border {
              border-color: #6B46C1;
            }
            .main-bg {
              background: linear-gradient(135deg, #F5F1E8 0%, #E8E0D0 100%);
            }
            .sidebar-bg {
              background: linear-gradient(180deg, #FEFCF8 0%, #F7F3E8 100%);
              border-right: 1px solid #E2E8F0;
            }
            .text-dark {
              color: #1A202C;
            }
            .text-muted {
              color: #718096;
            }
            .play-item {
              cursor: pointer;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
              border-radius: 8px;
              margin: 2px 8px;
              padding: 12px 16px;
            }
            .play-item:hover {
              background-color: #D1F2EB;
              transform: translateX(4px);
              box-shadow: 0 2px 8px rgba(45, 90, 39, 0.15);
            }
            .play-item.active {
              background: linear-gradient(135deg, #6B46C1 0%, #553C9A 100%);
              color: white;
              box-shadow: 0 4px 12px rgba(107, 70, 193, 0.3);
            }
            .search-input {
              background-color: #FEFCF8;
              border: 2px solid #E2E8F0;
              transition: all 0.3s ease;
            }
            .search-input:focus {
              border-color: #6B46C1;
              box-shadow: 0 0 0 3px rgba(107, 70, 193, 0.1);
              transform: translateY(-1px);
            }
            .tab-button {
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
              position: relative;
            }
            .tab-button.active {
              border-bottom: 3px solid #6B46C1;
              color: #6B46C1;
              font-weight: 600;
            }
            .tab-button.active::after {
              content: '';
              position: absolute;
              bottom: -3px;
              left: 0;
              right: 0;
              height: 3px;
              background: linear-gradient(90deg, #6B46C1 0%, #553C9A 100%);
              border-radius: 2px;
            }
            .quote-block {
              margin-left: 2rem;
              margin-bottom: 1.5rem;
              font-style: italic;
              border-left: 4px solid #6B46C1;
              padding-left: 1.5rem;
              background: linear-gradient(135deg, #E6FFFA 0%, #D1F2EB 100%);
              padding: 1.5rem;
              border-radius: 12px;
              font-family: 'Courier New, monospace';
              box-shadow: 0 4px 12px rgba(45, 90, 39, 0.15);
              position: relative;
            }
            .quote-block::before {
              content: '"';
              position: absolute;
              top: -10px;
              left: -5px;
              font-size: 3rem;
              color: #6B46C1;
              font-family: 'Playfair Display, serif';
            }
            .section-header {
              font-weight: 700;
              color: #1A202C;
              margin-top: 2rem;
              margin-bottom: 1rem;
              font-size: 1.25rem;
              font-family: 'Inter, sans-serif';
              position: relative;
              padding-left: 1rem;
            }
            .section-header::before {
              content: '';
              position: absolute;
              left: 0;
              top: 50%;
              transform: translateY(-50%);
              width: 4px;
              height: 24px;
              background: linear-gradient(180deg, #6B46C1 0%, #553C9A 100%);
              border-radius: 2px;
            }
            .card {
              background: #FEFCF8;
              border-radius: 16px;
              box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
              border: 1px solid #E2E8F0;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .card:hover {
              transform: translateY(-2px);
              box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            }
            .button-primary {
              background: linear-gradient(135deg, #6B46C1 0%, #553C9A 100%);
              color: white;
              border: none;
              border-radius: 12px;
              padding: 12px 24px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
              box-shadow: 0 4px 12px rgba(107, 70, 193, 0.3);
            }
            .button-primary:hover {
              transform: translateY(-2px);
              box-shadow: 0 6px 20px rgba(107, 70, 193, 0.4);
            }
            .button-secondary {
              background: transparent;
              color: #6B46C1;
              border: 2px solid #6B46C1;
              border-radius: 12px;
              padding: 10px 20px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .button-secondary:hover {
              background: #6B46C1;
              color: white;
              transform: translateY(-1px);
            }
            .source-card {
              background: linear-gradient(135deg, #E6FFFA 0%, #D1F2EB 100%);
              border: 1px solid #A7F3D0;
              border-radius: 12px;
              padding: 1.5rem;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .source-card:hover {
              transform: translateY(-2px);
              box-shadow: 0 8px 25px rgba(45, 90, 39, 0.2);
            }
            .similarity-badge {
              background: linear-gradient(135deg, #6B46C1 0%, #553C9A 100%);
              color: white;
              padding: 6px 12px;
              border-radius: 20px;
              font-size: 0.875rem;
              font-weight: 600;
              box-shadow: 0 2px 8px rgba(107, 70, 193, 0.3);
            }
            .status-indicator {
              width: 12px;
              height: 12px;
              border-radius: 50%;
              background: linear-gradient(135deg, #48BB78 0%, #38A169 100%);
              box-shadow: 0 0 0 3px rgba(72, 187, 120, 0.2);
              animation: pulse 2s infinite;
            }
            @keyframes pulse {
              0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.4); }
              70% { box-shadow: 0 0 0 6px rgba(72, 187, 120, 0); }
              100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
            }
            .title-gradient {
              background: linear-gradient(135deg, #6B46C1 0%, #553C9A 50%, #2D5A27 100%);
              -webkit-background-clip: text;
              -webkit-text-fill-color: transparent;
              background-clip: text;
            }
          `
        }} />
      </Head>

      <main style={{ background: 'linear-gradient(135deg, #F5F1E8 0%, #E8E0D0 100%)', fontFamily: 'Inter, sans-serif', minHeight: '100vh' }}>
        <div style={{ display: 'flex', height: '100vh' }}>
          {/* Sidebar */}
                      <div style={{ width: '320px', background: 'linear-gradient(180deg, #FEFCF8 0%, #F7F3E8 100%)', borderRight: '1px solid #E2E8F0', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', overflowY: 'auto' }}>
            {/* Filter Toggle */}
            <div style={{ padding: '16px', borderBottom: '1px solid #718096' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={showTragediesOnly}
                  onChange={(e) => setShowTragediesOnly(e.target.checked)}
                  style={{ borderRadius: '4px' }}
                />
                <span style={{ fontSize: '14px', color: '#6B46C1', fontWeight: '500' }}>Show Tragedies Only</span>
              </label>
            </div>

            {/* Selected Play Display */}
            {selectedPlay && (
              <div style={{ padding: '16px', borderBottom: '1px solid #718096', backgroundColor: '#f7fafc' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                                      <div style={{ fontSize: '14px', fontWeight: '600', color: '#6B46C1' }}>Selected Play:</div>
                  <div style={{ fontSize: '12px', color: '#1A202C' }}>{selectedPlay.title}</div>
                  </div>
                  <button
                    onClick={() => setSelectedPlay(null)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      fontWeight: '600',
                      boxShadow: '0 2px 8px rgba(107, 70, 193, 0.3)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(107, 70, 193, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(107, 70, 193, 0.3)';
                    }}
                  >
                    Deselect
                  </button>
                </div>
              </div>
            )}

            {/* Plays List */}
            <div style={{ padding: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#6B46C1', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Plays</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {filteredPlays.map((play, index) => (
                  <div
                    key={index}
                    onClick={() => selectPlay(play)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      cursor: 'pointer',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      backgroundColor: selectedPlay?.title === play.title ? 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)' : 'transparent',
                      color: selectedPlay?.title === play.title ? 'white' : '#1A202C',
                      margin: '2px 8px',
                      boxShadow: selectedPlay?.title === play.title ? '0 4px 12px rgba(107, 70, 193, 0.3)' : 'none'
                    }}
                    onMouseEnter={(e) => {
                      if (selectedPlay?.title !== play.title) {
                        e.currentTarget.style.backgroundColor = '#E6FFFA';
                        e.currentTarget.style.transform = 'translateX(4px)';
                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(45, 90, 39, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedPlay?.title !== play.title) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.transform = 'translateX(0)';
                        e.currentTarget.style.boxShadow = 'none';
                      }
                    }}
                  >
                    <div style={{ fontWeight: '500' }}>{play.title}</div>
                    <div style={{ fontSize: '12px', color: selectedPlay?.title === play.title ? 'rgba(255,255,255,0.7)' : '#2D5A27', opacity: 0.8 }}>{play.category}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ padding: '24px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#FEFCF8' }}>
              <div style={{ maxWidth: '1024px', margin: '0 auto' }}>
                <h1 style={{ 
                  fontSize: '36px', 
                  fontWeight: '800', 
                  margin: 0, 
                  fontFamily: 'Inter, sans-serif',
                  letterSpacing: '0.5px',
                  background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 50%, #2D5A27 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  Shakespeare GPT
                </h1>
                <p style={{ 
                  color: '#2D5A27', 
                  margin: '8px 0 0 0',
                  fontFamily: 'Inter, sans-serif',
                  fontSize: '18px',
                  fontWeight: '500'
                }}>Ask questions about Shakespeare's works</p>
              </div>
            </div>

            {/* Main Content Area */}
            <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
              <div style={{ maxWidth: '1024px', margin: '0 auto' }}>
                {/* Info Bar */}
                <div style={{ backgroundColor: '#FEFCF8', borderRadius: '16px', padding: '20px', marginBottom: '24px', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)', border: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'linear-gradient(135deg, #48BB78 0%, #38A169 100%)', boxShadow: '0 0 0 3px rgba(72, 187, 120, 0.2)', animation: 'pulse 2s infinite' }}></div>
                      <span style={{ fontSize: '16px', color: '#1A202C', fontWeight: '500' }}>
                        {selectedPlay 
                          ? `Searching within: ${selectedPlay.title} (${selectedPlay.category})`
                          : 'Searching across all Shakespeare plays'
                        }
                      </span>
                    </div>
                    {selectedPlay && (
                      <button
                        onClick={() => setSelectedPlay(null)}
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          backgroundColor: 'transparent',
                          color: '#6B46C1',
                          border: '2px solid #6B46C1',
                          borderRadius: '12px',
                          cursor: 'pointer',
                          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          fontWeight: '600'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = '#6B46C1';
                          e.currentTarget.style.color = 'white';
                          e.currentTarget.style.transform = 'translateY(-1px)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = '#6B46C1';
                          e.currentTarget.style.transform = 'translateY(0)';
                        }}
                      >
                        Clear Filter
                      </button>
                    )}
                  </div>
                </div>

                {/* Search Input - Centered */}
                <div style={{ marginBottom: '32px' }}>
                  <div style={{ maxWidth: '512px', margin: '0 auto' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder={selectedPlay ? `Ask about ${selectedPlay.title}...` : "Ask about Shakespeare's plays, characters, or themes..."}
                        style={{
                          flex: 1,
                          padding: '16px 20px',
                          border: '2px solid #E2E8F0',
                          borderRadius: '12px',
                          fontSize: '16px',
                          backgroundColor: '#FEFCF8',
                          outline: 'none',
                          transition: 'all 0.3s ease'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#6B46C1';
                          e.target.style.boxShadow = '0 0 0 3px rgba(107, 70, 193, 0.1)';
                          e.target.style.transform = 'translateY(-1px)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#E2E8F0';
                          e.target.style.boxShadow = 'none';
                          e.target.style.transform = 'translateY(0)';
                        }}
                        onKeyPress={(e) => e.key === 'Enter' && askQuestion()}
                      />
                      <button
                        onClick={askQuestion}
                        disabled={loading || !question.trim()}
                        style={{
                          padding: '16px 28px',
                          color: 'white',
                          fontWeight: '600',
                          borderRadius: '12px',
                          background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)',
                          border: 'none',
                          cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          boxShadow: '0 4px 12px rgba(107, 70, 193, 0.3)',
                          opacity: loading || !question.trim() ? 0.5 : 1
                        }}
                        onMouseEnter={(e) => {
                          if (!loading && question.trim()) {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 6px 20px rgba(107, 70, 193, 0.4)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!loading && question.trim()) {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(107, 70, 193, 0.3)';
                          }
                        }}
                      >
                        {loading ? '🧐 Thinking...' : 'Send'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Error Message */}
                {error && (
                  <div style={{ maxWidth: '512px', margin: '0 auto 24px auto' }}>
                    <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '12px 16px', borderRadius: '8px' }}>
                      ❌ {error}
                    </div>
                  </div>
                )}

                {/* Answer Section */}
                {answer && (
                  <div style={{ maxWidth: '1024px', margin: '0 auto' }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                      {/* Question Display */}
                      <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#6B46C1', margin: '0 0 8px 0' }}>
                          Question
                        </h3>
                        <p style={{ color: '#374151', margin: 0 }}>{question}</p>
                      </div>



                      {/* Answer Content */}
                      <div style={{ padding: '24px' }}>
                        <div style={{ 
                          color: '#374151', 
                          lineHeight: '1.8', 
                          fontSize: '16px',
                          fontFamily: 'Courier New, monospace'
                        }}>
                          <ReactMarkdown
                            components={{
                              h1: ({children}) => <h1 style={{fontSize: '1.5rem', fontWeight: '600', color: '#6B46C1', marginTop: '1.5rem', marginBottom: '0.5rem', fontFamily: 'Courier New, monospace'}}>{children}</h1>,
                              h2: ({children}) => <h2 style={{fontSize: '1.3rem', fontWeight: '600', color: '#6B46C1', marginTop: '1.5rem', marginBottom: '0.5rem', fontFamily: 'Courier New, monospace'}}>{children}</h2>,
                              h3: ({children}) => <h3 style={{fontSize: '1.1rem', fontWeight: '600', color: '#6B46C1', marginTop: '1.5rem', marginBottom: '0.5rem', fontFamily: 'Courier New, monospace'}}>{children}</h3>,
                              strong: ({children}) => <strong style={{fontWeight: '600', color: '#6B46C1', fontFamily: 'Courier New, monospace'}}>{children}</strong>,
                              em: ({children}) => <em style={{fontStyle: 'italic', color: '#2D5A27', fontFamily: 'Courier New, monospace'}}>{children}</em>,
                              blockquote: ({children}) => (
                                <div style={{
                                  marginLeft: '2rem',
                                  marginBottom: '1rem',
                                  fontStyle: 'italic',
                                  borderLeft: '4px solid #6B46C1',
                                  paddingLeft: '1.5rem',
                                  background: 'linear-gradient(135deg, #F0FFF4 0%, #E6FFFA 100%)',
                                  padding: '1.5rem',
                                  borderRadius: '12px',
                                  fontSize: '15px',
                                  fontFamily: 'Courier New, monospace',
                                  boxShadow: '0 4px 12px rgba(45, 90, 39, 0.1)',
                                  position: 'relative'
                                }}>
                                  {children}
                                </div>
                              ),
                              p: ({children}) => {
                                const text = children?.toString() || '';
                                
                                // Handle line breaks by converting / to actual line breaks
                                if (text.includes('/')) {
                                  const lines = text.split('/').map((line, index) => (
                                    <span key={index}>
                                      {line.trim()}
                                      {index < text.split('/').length - 1 && <br />}
                                    </span>
                                  ));
                                  
                                  // Check if this paragraph contains a quote or Act/Scene reference
                                  if (text.includes('(Act') || text.includes('(Scene') || text.trim().startsWith('"')) {
                                    return (
                                      <div style={{
                                        marginLeft: '2rem',
                                        marginBottom: '1rem',
                                        fontStyle: 'italic',
                                        borderLeft: '4px solid #6B46C1',
                                        paddingLeft: '1.5rem',
                                        background: 'linear-gradient(135deg, #F0FFF4 0%, #E6FFFA 100%)',
                                        padding: '1.5rem',
                                        borderRadius: '12px',
                                        fontSize: '15px',
                                        fontFamily: 'Courier New, monospace',
                                        boxShadow: '0 4px 12px rgba(45, 90, 39, 0.1)',
                                        position: 'relative'
                                      }}>
                                        {lines}
                                      </div>
                                    );
                                  }
                                  
                                  return <p style={{marginBottom: '1rem', fontFamily: 'Courier New, monospace', lineHeight: '1.6'}}>{lines}</p>;
                                }
                                
                                // Check if this paragraph contains a quote or Act/Scene reference
                                if (text.includes('(Act') || text.includes('(Scene') || text.trim().startsWith('"')) {
                                  return (
                                    <div style={{
                                      marginLeft: '2rem',
                                      marginBottom: '1rem',
                                      fontStyle: 'italic',
                                      borderLeft: '4px solid #6B46C1',
                                      paddingLeft: '1.5rem',
                                      background: 'linear-gradient(135deg, #F0FFF4 0%, #E6FFFA 100%)',
                                      padding: '1.5rem',
                                      borderRadius: '12px',
                                      fontSize: '15px',
                                      fontFamily: 'Courier New, monospace',
                                      boxShadow: '0 4px 12px rgba(45, 90, 39, 0.1)',
                                      position: 'relative'
                                    }}>
                                      {children}
                                    </div>
                                  );
                                }
                                return <p style={{marginBottom: '1rem', fontFamily: 'Courier New, monospace', lineHeight: '1.6'}}>{children}</p>;
                              }
                            }}
                          >
                            {answer}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Sources */}
                {sources.length > 0 && (
                  <div style={{ maxWidth: '1024px', margin: '24px auto 0 auto' }}>
                    <div style={{ backgroundColor: '#FEFCF8', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)', border: '1px solid #E2E8F0', padding: '24px' }}>
                      <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#6B46C1', margin: '0 0 16px 0' }}>
                        📚 Sources
                      </h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {sources.map((source, index) => (
                          <div key={index} style={{ 
                            background: 'linear-gradient(135deg, #F0FFF4 0%, #E6FFFA 100%)', 
                            borderRadius: '12px', 
                            padding: '20px', 
                            border: '1px solid #C6F6D5',
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 8px 25px rgba(45, 90, 39, 0.15)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = 'none';
                          }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div>
                                <h4 style={{ fontWeight: '600', color: '#6B46C1', margin: '0 0 4px 0' }}>
                                  {source.play} - {source.act}
                                </h4>
                                <p style={{ color: '#6B46C1', fontSize: '14px', margin: 0 }}>
                                  {source.scene_title.split('.')[0]}
                                </p>
                              </div>
                              <span style={{ 
                                fontSize: '12px', 
                                background: 'linear-gradient(135deg, #6B46C1 0%, #553C9A 100%)', 
                                color: 'white', 
                                padding: '6px 12px', 
                                borderRadius: '20px',
                                fontWeight: '600',
                                boxShadow: '0 2px 8px rgba(107, 70, 193, 0.3)'
                              }}>
                                {source.similarity}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
} 