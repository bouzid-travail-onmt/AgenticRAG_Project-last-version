// src/components/MessageInput.js
import React, { useState, useEffect, useRef } from "react";
import "../styles/MessageInput.css";
import { askQuestion } from "../services/ragService";
import TypingAnimation from "./TypingAnimation";
import { Copy, Pencil } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { initialBotMessages } from "../services/conversationsService";

const MessageInput = ({ conversation, onCreateConversation, onUpdateConversation }) => {
  const [messages, setMessages] = useState(conversation ? conversation.messages : initialBotMessages);
  const [input, setInput] = useState("");
  const [conversationStarted, setConversationStarted] = useState(!!conversation);
  const [thinkingTime, setThinkingTime] = useState(0); // ⏳ compteur en secondes
  const [typingText, setTypingText] = useState(""); // texte en streaming
  const messagesEndRef = useRef(null);

  // Scroll automatique
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingText]);

  // Synchroniser avec prop conversation
  useEffect(() => {
    if (conversation) {
      setMessages(conversation.messages || []);
      setConversationStarted(true);
    } else {
      setMessages(initialBotMessages);
      setConversationStarted(false);
    }
    setTypingText("");
    setThinkingTime(0);
  }, [conversation]);

  // Timer basé sur le dernier bot en train de taper
  useEffect(() => {
    const lastTypingBot = messages.slice().reverse().find((msg) => msg.role === "bot" && msg.isTyping);
    let timer;

    if (lastTypingBot) {
      setThinkingTime(0); // reset compteur
      timer = setInterval(() => {
        setThinkingTime((prev) => prev + 1);
      }, 1000);
    } else {
      setThinkingTime(0);
    }

    return () => clearInterval(timer);
  }, [messages]);

  const persistMessages = (convId, newMessages, maybeTitle) => {
    if (onUpdateConversation) {
      const updates = { messages: newMessages };
      if (maybeTitle) updates.title = maybeTitle;
      onUpdateConversation(convId, updates);
    }
  };

  const handleSend = async (e) => {
    e?.preventDefault?.();
    if (!input.trim()) return;

    let conv = conversation;
    if (!conv) {
      if (onCreateConversation) conv = onCreateConversation();
      else conv = null;
    }

    const userMessage = { role: "user", content: input.trim(), createdAt: new Date().toISOString() };

    // Ajouter le message utilisateur
    setMessages((prev) => {
      const next = [...prev, userMessage];
      if (conv && conv.id) {
        const isFirstUserMessage = !conv.title && !prev.some((m) => m.role === "user");
        const maybeTitle = isFirstUserMessage ? userMessage.content : undefined;
        persistMessages(conv.id, next, maybeTitle);
      }
      return next;
    });

    setInput("");
    setTypingText("");

    // Ajouter placeholder bot avec isTyping
    setMessages((prev) => {
      const next = [
        ...prev,
        { role: "bot", content: "", createdAt: new Date().toISOString(), isTyping: true }
      ];
      if (conv && conv.id) persistMessages(conv.id, next);
      return next;
    });

    try {
      const fullReply = await askQuestion(input.trim());
      const words = fullReply.split(" ");
      let i = 0;

      const wordInterval = setInterval(() => {
        if (i < words.length) {
          setTypingText((prev) => (prev ? prev + " " + words[i] : words[i]));
          i++;
        } else {
          clearInterval(wordInterval);

          // Mettre à jour le message bot final
          setMessages((prev) => {
            const lastIndex = prev.length - 1;
            const updated = prev.map((msg, idx) =>
              idx === lastIndex ? { ...msg, content: fullReply, isTyping: false } : msg
            );
            if (conv && conv.id) persistMessages(conv.id, updated);
            return updated;
          });

          setTypingText("");
        }
      }, 120);
    } catch (err) {
      console.error("askQuestion error", err);
      setMessages((prev) => {
        const lastIndex = prev.length - 1;
        const updated = prev.map((msg, idx) =>
          idx === lastIndex ? { ...msg, content: "Erreur lors de la génération de la réponse.", isTyping: false } : msg
        );
        if (conv && conv.id) persistMessages(conv.id, updated);
        return updated;
      });
      setTypingText("");
    }
  };

  const handleCopy = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
  };

  const handleEdit = (idx) => {
    const oldMessage = messages[idx];
    if (!oldMessage) return;
    setInput(oldMessage.content);
    setMessages((prev) => {
      const next = prev.filter((_, i) => i !== idx);
      if (conversation && conversation.id) persistMessages(conversation.id, next);
      return next;
    });
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className="message-wrapper">
            <div className={`message ${msg.role}`}>
              {msg.role === "bot" && msg.isTyping ? (
                <div>
                  <TypingAnimation text={typingText} />
                  <div className="thinking-timer">⏳ {thinkingTime}s</div>
                </div>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              )}
            </div>

            <div className="message-actions">
              <button className="action-btn" onClick={() => handleCopy(msg.content)} title="Copier">
                <Copy size={10} />
              </button>
              {msg.role === "user" && (
                <button className="action-btn" onClick={() => handleEdit(idx)} title="Modifier">
                  <Pencil size={10} />
                </button>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-container" onSubmit={handleSend}>
        <input
          type="text"
          className="chat-input"
          placeholder="Chercher votre indicateur,pour la perticence consulter les indicateurs avant de chercher ..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className={`send-button ${input.trim() ? "active" : ""}`}>
          ➤
        </button>
      </form>
    </div>
  );
};

export default MessageInput;
