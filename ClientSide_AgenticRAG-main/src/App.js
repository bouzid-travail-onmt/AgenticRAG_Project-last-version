// src/App.js
import React, { useEffect, useState } from "react";
import "./styles.css";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MessageInput from "./components/MessageInput";
import Login from "./components/Login";
import ProcessData from "./components/ProcessData";
import * as conversationsService from "./services/conversationsService";

function App() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showProcessData, setShowProcessData] = useState(false); // ✅ nouveau

  useEffect(() => {
    setConversations(conversationsService.loadConversations());
  }, []);

  const handleNewConversation = () => {
    const conv = conversationsService.createConversation();
    setConversations(conversationsService.loadConversations());
    setActiveConversationId(conv.id);
    return conv;
  };

  const handleSelectConversation = (id) => {
    setActiveConversationId(id);
    setSidebarOpen(false);
  };

  const handleDeleteConversation = (id) => {
    conversationsService.deleteConversation(id);
    setConversations(conversationsService.loadConversations());
    if (activeConversationId === id) setActiveConversationId(null);
  };

  const handleUpdateConversation = (id, updates) => {
    conversationsService.updateConversation(id, updates);
    setConversations(conversationsService.loadConversations());
  };

  const handleShowLogin = () => setShowLogin(true);
  const handleCloseLogin = () => setShowLogin(false);
  const handleOpenProcessData = () => setShowProcessData(true);
  const handleCloseProcessData = () => setShowProcessData(false);

  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) || null;

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        activeConversationId={activeConversationId}
        className={sidebarOpen ? "open" : ""}
        onShowLogin={handleShowLogin}
      />

      <div className="main-content">
        <div className="mobile-header">
          <button
            className="hamburger-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
        </div>

        {!showLogin && !showProcessData && (
          <MessageInput
            conversation={activeConversation}
            onCreateConversation={handleNewConversation}
            onUpdateConversation={handleUpdateConversation}
          />
        )}

        {showLogin && (
          <Login
            onClose={handleCloseLogin}
            onSuccess={handleOpenProcessData} // ✅ ouvre ProcessData après login
          />
        )}

        {showProcessData && <ProcessData onClose={handleCloseProcessData} />}
      </div>
    </div>
  );
}

export default App;
