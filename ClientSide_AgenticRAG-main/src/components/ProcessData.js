// src/components/ProcessData.js
import React, { useState } from "react";
import {
  FiUpload,
  FiX,
  FiCheck,
  FiLogOut,
  FiEye,
  FiEyeOff,
  FiDatabase,
  FiRefreshCw,   // ✅ ajouté
} from "react-icons/fi";
import { FiCpu } from "react-icons/fi"; // icône Preprocessing
import ViewData from "./ViewData";
import DataPreprocessing from "./DataPreprocessing";
import "../styles/ProcessData.css";
import { getAuthHeaders, logout } from "../services/loginService";
import { uploadData } from "../services/ProcessDataService";

export default function ProcessData({ onClose }) {
  const [files, setFiles] = useState([]);
  const [urls, setUrls] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showViewData, setShowViewData] = useState(false);
  const [showPreprocessing, setShowPreprocessing] = useState(false);
  const [status, setStatus] = useState("info");

  // 🔄 RESET DU COMPOSANT
  const handleReset = () => {
    setFiles([]);
    setUrls("");
    setMessage("");
    setLoading(false);
    setResult(null);
    setShowResult(false);
    setShowLogs(false);
    setShowViewData(false);
    setShowPreprocessing(false);
    setStatus("info");
  };

  // Sélection des fichiers
  const handleFiles = (e) => {
    const incoming = Array.from(e.target.files);
    const allowed = ["pdf", "xls", "xlsx", "json", "txt"];
    const filtered = incoming.filter((f) => {
      const ext = f.name.split(".").pop().toLowerCase();
      return allowed.includes(ext);
    });
    if (filtered.length !== incoming.length) {
      alert("⚠️ Certains fichiers ont été ignorés (format non supporté).");
    }
    setFiles((prev) => [...prev, ...filtered]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Extraction du résumé depuis les logs
  const parseSummaryFromLog = (data) => {
    const match = data.match(/✅\s*(\d+)\s*insérés.*⚠️\s*(\d+)\s*déjà.*❌\s*(\d+)/);
    if (!match) return { inserted: 0, existing: 0, errors: 0 };
    return {
      inserted: parseInt(match[1]),
      existing: parseInt(match[2]),
      errors: parseInt(match[3]),
    };
  };

  // Upload
  const handleValidate = async () => {
    if (files.length === 0 && !urls.trim()) {
      setMessage("⚠️ Ajoute des fichiers ou au moins une URL avant de valider.");
      return;
    }

    setMessage("");
    setLoading(true);
    setResult(null);
    setShowResult(true);
    setShowLogs(false);

    try {
      const { data } = await uploadData(files, urls, getAuthHeaders());
      setResult(data);

      const { inserted, existing, errors } = parseSummaryFromLog(data);
      let summaryMessage = "";
      let currentStatus = "info";

      if (errors > 0) {
        summaryMessage = `❌ ${errors} fichier(s) n’ont pas pu être traités.`;
        currentStatus = "error";
      } else if (inserted > 0 && existing === 0) {
        summaryMessage = `✅ ${inserted} fichier(s) inséré(s) avec succès.`;
        currentStatus = "success";
      } else if (inserted > 0 && existing > 0) {
        summaryMessage = `⚠️ ${inserted} fichier(s) inséré(s), ${existing} déjà existant(s).`;
        currentStatus = "warning";
      } else if (inserted === 0 && existing > 0) {
        summaryMessage = `⚠️ Aucun nouveau fichier inséré — ${existing} déjà existant(s).`;
        currentStatus = "warning";
      } else {
        summaryMessage = "ℹ️ Aucun changement détecté.";
      }

      setMessage(summaryMessage);
      setStatus(currentStatus);
    } catch (err) {
      console.error("❌ Erreur dans handleValidate :", err);
      setMessage(
        `❌ Erreur réseau ou serveur : ${err.response?.data?.detail || err.message}`
      );
      setStatus("error");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm("Êtes-vous sûr de vouloir vous déconnecter ?")) {
      logout();
      alert("✅ Déconnexion réussie.");
      onClose();
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case "success":
        return "#28a745";
      case "warning":
        return "#ff9800";
      case "error":
        return "#f44336";
      default:
        return "#007bff";
    }
  };

  return (
    <div className="admin-overlay">
      <div className="admin-panel">
        <div className="admin-header">
          <h2>Admin — Mise à jour des données</h2>
          <div className="admin-actions">

            {/* 🔄 BOUTON REFRESH */}
            <button
              className="refresh-btn"
              onClick={handleReset}
              title="Réinitialiser"
              disabled={loading}
            >
              <FiRefreshCw size={18} />
            </button>

            <button
              className="logout-btn"
              onClick={handleLogout}
              title="Se déconnecter"
              disabled={loading}
            >
              <FiLogOut size={18} />
            </button>

            <button
              className="close-btn"
              onClick={onClose}
              title="Fermer"
              disabled={loading}
            >
              <FiX size={18} />
            </button>
          </div>
        </div>

        <div className={`admin-body ${loading ? "loading" : ""}`}>
          {/* Fichiers */}
          <label className="file-input">
            <FiUpload /> Choisir des fichiers (pdf, xlsx, xls, txt, json)
            <input type="file" multiple onChange={handleFiles} disabled={loading} />
          </label>

          {/* URLs */}
          <div className="url-input">
            <textarea
              rows={3}
              placeholder="URLs à scraper (séparées par virgule ou retour à la ligne)"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              disabled={loading}
            />
          </div>

          {/* Liste fichiers */}
          <div className="file-list">
            <h4>Fichiers sélectionnés</h4>
            {files.length === 0 ? (
              <div className="empty">Aucun fichier</div>
            ) : (
              <ul>
                {files.map((f, i) => (
                  <li key={i}>
                    <div className="file-item">
                      <span className="file-name">{f.name}</span>
                      <span className={`ext ext-${f.name.split(".").pop().toLowerCase()}`}>
                        .{f.name.split(".").pop()}
                      </span>
                    </div>
                    <button
                      className="remove"
                      onClick={() => removeFile(i)}
                      disabled={loading}
                    >
                      Supprimer
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Actions */}
          <div className="actions">
            <button className="btn-validate" onClick={handleValidate} disabled={loading}>
              {loading ? "Traitement..." : (<><FiCheck /> Insérer </>)}
            </button>

            <button
              className="btn-access-data"
              onClick={() => setShowViewData(true)}
              disabled={loading}
            >
              <FiDatabase size={18} style={{ marginRight: "6px" }} />
              Voir les données d'alimentations
            </button>

            <button
              className="btn-access-data"
              onClick={() => setShowPreprocessing(true)}
              disabled={loading}
            >
              <FiCpu size={18} style={{ marginRight: "6px" }} />
              Preprocessing
            </button>

            <button className="btn-cancel" onClick={onClose} disabled={loading}>
              Annuler
            </button>
          </div>

          {/* Message */}
          {message && (
            <div
              className={`message message-${status}`}
              style={{
                borderLeft: `4px solid ${getStatusColor()}`,
                color: getStatusColor(),
              }}
            >
              {message}
              {showResult && result && (
                <button
                  className="eye-btn"
                  onClick={() => setShowLogs((prev) => !prev)}
                  title={showLogs ? "Masquer les logs" : "Afficher les logs"}
                  style={{
                    background: "transparent",
                    border: "none",
                    marginLeft: "10px",
                    cursor: "pointer",
                    color: getStatusColor(),
                  }}
                >
                  {showLogs ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                </button>
              )}
            </div>
          )}

          {/* Logs */}
          {showLogs && result && (
            <div className="result">
              <strong>📜 Journal complet :</strong>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  background: "#0b0b0b",
                  color: "#00ff7f",
                  padding: "10px",
                  borderRadius: "8px",
                  maxHeight: "300px",
                  overflowY: "auto",
                  marginTop: "10px",
                }}
              >
                {result}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Overlays */}
      {showViewData && <ViewData onClose={() => setShowViewData(false)} />}
      {showPreprocessing && (
        <DataPreprocessing onClose={() => setShowPreprocessing(false)} />
      )}
    </div>
  );
}
