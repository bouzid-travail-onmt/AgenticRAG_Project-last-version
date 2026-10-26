// src/components/DataPreprocessing.js
import React, { useState, useEffect } from "react";
import { FiArrowLeft, FiCheckCircle, FiFileText } from "react-icons/fi";
import { FaFileExcel } from "react-icons/fa";
import "../styles/DataPreprocessing.css";
import {
  startPreprocessingExcels,
  startPreprocessingReports,
} from "../services/DataPreprocessingService";
import { fetchFilesRecent } from "../services/ViewDataService";

export default function DataPreprocessing({ onClose }) {
  const [activeSection, setActiveSection] = useState("");
  const [excelFiles, setExcelFiles] = useState([]);
  const [reportFiles, setReportFiles] = useState([]);
  const [logsExcel, setLogsExcel] = useState([]);
  const [logsReports, setLogsReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [eventSource, setEventSource] = useState(null);
  const [showLogs, setShowLogs] = useState(false);
  const [toast, setToast] = useState("");

  // Helper pour sélectionner les logs actifs
  const getLogs = (type) => (type === "excel" ? logsExcel : logsReports);
  const setLogs = (type) => (type === "excel" ? setLogsExcel : setLogsReports);

  // 🔹 Fetch récents Excel
  const handleFetchRecentExcels = async () => {
    setLoading(true);
    try {
      const data = await fetchFilesRecent("excel");
      setExcelFiles(Array.isArray(data) ? data : data.files || []);
    } catch (err) {
      console.error("❌ Erreur fetch Excel :", err);
      alert("❌ Impossible de charger les fichiers Excel récents.");
    } finally {
      setLoading(false);
    }
  };

  // 🔹 Fetch récents Reports
  const handleFetchRecentReports = async () => {
    setLoading(true);
    try {
      const data = await fetchFilesRecent("pdf");
      setReportFiles(Array.isArray(data) ? data : data.files || []);
    } catch (err) {
      console.error("❌ Erreur fetch Rapports :", err);
      alert("❌ Impossible de charger les rapports récents.");
    } finally {
      setLoading(false);
    }
  };

  // 🔹 Lancer preprocessing avec SSE
  const handleStartPreprocessing = async (type = "excel") => {
    setProcessing(true);
    setToast("");
    setLogs(type)(["🚀 Lancement du preprocessing..."]);
    setShowLogs(true);

    try {
      const sse =
        type === "excel"
          ? await startPreprocessingExcels()
          : await startPreprocessingReports();

      setEventSource(sse);

      sse.onopen = () => console.log("✅ SSE connecté");

      sse.onmessage = (event) => {
        const msg = event.data;
        const cleanMsg = msg.trim();

        // ✅ Messages finaux
        if (
          (type === "reports" && cleanMsg.includes("Pipeline complet terminé")) ||
          (type === "excel" && cleanMsg.includes("Fin du pipeline Excel"))
        ) {
          setProcessing(false);
          setToast("La mise à jour des données a été bien faite avec succès !");
          setTimeout(() => setToast(""), 5000);

          // 🔹 Fermer SSE
          if (sse) sse.close();
          return;
        }

        // Progression FAISS → remplacer dernière ligne
        if (msg.includes("Construction FAISS en cours")) {
          setLogs(type)((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = msg;
            return updated;
          });
        } else {
          setLogs(type)((prev) => [...prev, msg]);
        }
      };
    } catch (err) {
      console.error("❌ Erreur lancement preprocessing :", err);
      setLogs(type)((prev) => [...prev, "❌ Impossible de lancer le preprocessing."]);
      setProcessing(false);
    }
  };

  // 🔹 Fermer SSE à la sortie
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
        console.log("🛑 SSE fermé à la sortie du composant");
      }
    };
  }, [eventSource]);

  return (
    <div className="dataprep-overlay">
      {processing && <div className="blocking-overlay-logs"></div>}

      <div className="dataprep-panel">
        <div className="dataprep-header">
          <h2>⚙️ Préprocessing et mise à jour des données</h2>
          <button className="back-btn" onClick={onClose} disabled={processing}>
            <FiArrowLeft /> Retour
          </button>
        </div>

        {toast && <div className="toast">✅ {toast}</div>}

        <div className="dataprep-main-buttons">
          <button
            className={`big-btn ${activeSection === "rapports" ? "active" : ""}`}
            onClick={() => {
              setActiveSection("rapports");
              handleFetchRecentReports();
            }}
            disabled={processing}
          >
            <FiFileText size={28} /> Rapports
          </button>

          <button
            className={`big-btn ${activeSection === "excels" ? "active" : ""}`}
            onClick={() => {
              setActiveSection("excels");
              handleFetchRecentExcels();
            }}
            disabled={processing}
          >
            <FaFileExcel size={28} color="#217346" /> Excels
          </button>
        </div>

        <div className="dataprep-content">
          {/* SECTION EXCEL */}
          {activeSection === "excels" && (
            <div className="excels-section">
              {loading && <div className="loading">⏳ Chargement des fichiers récents...</div>}

              {!loading && excelFiles.length > 0 && (
                <>
                  <h3>📅 Fichiers Excel ajoutés récemment (12 dernières heures)</h3>
                  <ul className="excel-list">
                    {excelFiles.map((f) => (
                      <li key={f.id}>
                        <strong>{f.name}</strong> — {new Date(f.createdAt).toLocaleString()}
                      </li>
                    ))}
                  </ul>
                  <button
                    className="validate-btn"
                    onClick={() => handleStartPreprocessing("excel")}
                    disabled={processing}
                  >
                    <FiCheckCircle size={20} /> Lancer le preprocessing & mise à jour
                  </button>
                </>
              )}

              {!loading && excelFiles.length === 0 && !processing && (
                <div className="empty">Aucun fichier Excel récent trouvé.</div>
              )}
            </div>
          )}

          {/* SECTION RAPPORTS */}
          {activeSection === "rapports" && (
            <div className="rapports-section">
              {loading && <div className="loading">⏳ Chargement des rapports récents...</div>}

              {!loading && reportFiles.length > 0 && (
                <>
                  <h3>📅 Rapports ajoutés récemment (12 dernières heures)</h3>
                  <ul className="excel-list">
                    {reportFiles.map((f) => (
                      <li key={f.id}>
                        <strong>{f.name}</strong> — {new Date(f.createdAt).toLocaleString()}
                      </li>
                    ))}
                  </ul>
                  <button
                    className="validate-btn"
                    onClick={() => handleStartPreprocessing("reports")}
                    disabled={processing}
                  >
                    <FiCheckCircle size={20} /> Lancer le preprocessing & mise à jour
                  </button>
                </>
              )}

              {!loading && reportFiles.length === 0 && !processing && (
                <div className="empty">Aucun rapport récent trouvé.</div>
              )}
            </div>
          )}

          {/* LOGS */}
          {(processing || logsExcel.length > 0 || logsReports.length > 0) && (
            <div className="logs-section" style={{ zIndex: 1000 }}>
              <div className="logs-header">
                <button
                  className="toggle-logs-btn"
                  onClick={() => setShowLogs(!showLogs)}
                >
                  {showLogs ? "👁️" : "👁️‍🗨️"}
                </button>
              </div>

              {showLogs && (
                <div className="logs-box">
                  {/* Logs Excel */}
                  {activeSection === "excels" &&
                    (logsExcel.length > 0 ? (
                      logsExcel.map((line, i) => (
                        <div key={i} className="log-line">
                          <span className="dot" /> {line}
                        </div>
                      ))
                    ) : (
                      <div className="log-line empty-log">
                        <span className="dot" /> Aucun log disponible.
                      </div>
                    ))}

                  {/* Logs Reports */}
                  {activeSection === "rapports" &&
                    (logsReports.length > 0 ? (
                      logsReports.map((line, i) => (
                        <div key={i} className="log-line">
                          <span className="dot" /> {line}
                        </div>
                      ))
                    ) : (
                      <div className="log-line empty-log">
                        <span className="dot" /> Aucun log disponible.
                      </div>
                    ))}

                  {/* Spinner */}
                  {processing && (
                    <div className="loading-spinner">
                      <span className="spinner-icon"></span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
