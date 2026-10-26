// src/components/Sidebar.js
import React, { useState } from "react";
import "../styles/Sidebar.css";
import { FiPlus, FiMessageSquare, FiRefreshCw, FiTrash2, FiLock } from "react-icons/fi";
import { FaChartBar } from "react-icons/fa"; // <-- icône pour Indicators
import IndicatorsView from "./IndicatorsView"; // <-- import du composant

export default function Sidebar({
  conversations = [],
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  activeConversationId,
  onShowLogin, // <-- trigger login
}) {
  const [open, setOpen] = useState(true);
  const [showIndicators, setShowIndicators] = useState(false); // pour toggle IndicatorsView

  const renderTitle = (conv) => {
    if (!conv) return "Nouvelle conversation";
    if (conv.title) return conv.title;
    const firstUser = conv.messages && conv.messages.find((m) => m.role === "user");
    if (firstUser && firstUser.content) {
      return firstUser.content.length > 40
        ? firstUser.content.slice(0, 40) + "..."
        : firstUser.content;
    }
    return "Nouvelle conversation";
  };

  return (
    <div className="sidebar">
      {open && (
        <div className="new-chat-dropdown">
          <button
            className="dropdown-item"
            onClick={() => onNewConversation && onNewConversation()}
            title="Nouvelle conversation"
          >
            <FiPlus className="icon" style={{ marginRight: "8px" }} />
            Nouvelle conversation
          </button>

          {/* Update data */}
          <button className="dropdown-item" onClick={onShowLogin}>
            <FiRefreshCw className="icon" style={{ marginRight: "8px" }} />
            Update data <span className="admin-badge"><FiLock style={{ marginRight: '4px' }} />Admin</span>
          </button>

          {/* Indicators button */}
          <button
            className="dropdown-item"
            onClick={() => setShowIndicators((prev) => !prev)}
          >
            <FaChartBar className="icon" style={{ marginRight: "8px" }} />
            Indicateurs
          </button>
        </div>
      )}

      {/* Affichage des IndicatorsView */}
      {showIndicators && (
        <div style={{ marginTop: "10px", borderTop: "1px solid #3a3f52", paddingTop: "10px" }}>
         <IndicatorsView /> {/* Public */}
        </div>
      )}

      <div className="history">
        <h4>Conversations</h4>
        <div className="history-list">
          {conversations.length === 0 && <div className="history-empty">Aucune conversation</div>}

          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`history-item ${activeConversationId === conv.id ? "active" : ""}`}
            >
              <div
                style={{ cursor: "pointer", display: "flex", alignItems: "center", flex: 1 }}
                onClick={() => onSelectConversation && onSelectConversation(conv.id)}
              >
                <FiMessageSquare className="icon" />
                <span style={{ marginLeft: 8 }}>{renderTitle(conv)}</span>
              </div>

              <div style={{ display: "flex", gap: 6 }}>
                <button
                  className="action-delete"
                  onClick={() => onDeleteConversation && onDeleteConversation(conv.id)}
                  title="Supprimer la conversation"
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    color: "red",
                  }}
                >
                  <FiTrash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
