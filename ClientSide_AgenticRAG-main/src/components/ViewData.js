// src/components/ViewData.js
import React, { useState } from "react";
import { FiX, FiDownload, FiEye, FiTrash2 } from "react-icons/fi";
import { SiElastic } from "react-icons/si";
import "../styles/ViewData.css";
import {
  fetchFiles,
  deleteFile,
  downloadFile,
  previewFile,
  fetchIndicatorsPrivate,
  deleteIndicator, 
  deleteAllFiles,// <-- ajout pour indicateurs
} from "../services/ViewDataService";
import ESAdminDashboard from "./EsManagement";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";
import * as XLSX from "xlsx"; // <-- pour Excel


export default function ViewData({ onClose }) {
  // ✅ États principaux
  const [activeType, setActiveType] = useState("");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [textPreview, setTextPreview] = useState(null);
  const [isJson, setIsJson] = useState(false);
  const [excelData, setExcelData] = useState(null);
  const [pageSize, setPageSize] = useState(30);
  const [searchTerm, setSearchTerm] = useState("");
  const [zoom, setZoom] = useState(100);
  // ✅ Pour indicateurs
  const [showIndicators, setShowIndicators] = useState(false);
  // ✅ Pour ElasticSearch
  const [showESAdmin, setShowESAdmin] = useState(false);
  const defaultLayoutPluginInstance = defaultLayoutPlugin();
  // ✅ Correction : exécuter la réinitialisation seulement au montage
 const resetAll = () => {
  setShowIndicators(false);
  setShowESAdmin(false);
  setActiveType("");

  // 🔥 Très important : fermer l'affichage des fichiers
  setFiles([]);
  setPreviewUrl(null);
  setExpandedFile(null);
};
  // ===============================
  // 🔹 Fonctions pour gérer les fichiers
  // ===============================
  const handleLoadFiles = async (type) => {
    setActiveType(type);
    setLoading(true);
    setFiles([]);
    setExpandedFile(null);
    setPreviewUrl(null);
    setTextPreview(null);
    setExcelData(null);
    try {
      const data = await fetchFiles(type);
      setFiles(data);
    } catch {
      alert("❌ Impossible de charger les fichiers.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (fileId) => {
    if (!window.confirm("Supprimer ce fichier ?")) return;
    try {
      await deleteFile(fileId, activeType);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
      if (expandedFile === fileId) {
        setExpandedFile(null);
        setPreviewUrl(null);
        setTextPreview(null);
        setExcelData(null);
      }
    } catch (err) {
      console.error("Erreur suppression:", err);
      alert("❌ Erreur lors de la suppression.");
    }
  };

  const handleDownload = async (fileId) => {
    try {
      await downloadFile(fileId, activeType);
    } catch {
      alert("❌ Erreur lors du téléchargement.");
    }
  };

  const handlePreview = async (fileId) => {
    setPreviewLoading(true);
    setPreviewUrl(null);
    setTextPreview(null);
    setExcelData(null);
    try {
      const url = await previewFile(fileId, activeType);
      setExpandedFile(fileId);

      if (activeType === "pdf") {
        setPreviewUrl(url);
      } else if (activeType === "txt" || activeType === "json") {
        const res = await fetch(url);
        const text = await res.text();

        if (activeType === "json") {
          try {
            const parsed = JSON.parse(text);
            const pretty = JSON.stringify(parsed, null, 2);
            setTextPreview(pretty);
            setIsJson(true);
          } catch {
            setTextPreview(text);
            setIsJson(false);
          }
        } else {
          setTextPreview(text);
          setIsJson(false);
        }
      } else if (activeType === "excel") {
        const res = await fetch(url);
        const blob = await res.blob();
        const arrayBuffer = await blob.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: "array", cellDates: true });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];

        // ✅ Lecture fidèle de la plage complète (avec cellules vides)
        const range = XLSX.utils.decode_range(sheet["!ref"]);
        const data = [];

        for (let R = range.s.r; R <= range.e.r; ++R) {
          const row = [];
          for (let C = range.s.c; C <= range.e.c; ++C) {
            const cellAddress = XLSX.utils.encode_cell({ r: R, c: C });
            const cell = sheet[cellAddress];

            if (!cell) {
              row.push("");
              continue;
            }

            let value = cell.v;
            const format = cell.z ? cell.z.toLowerCase() : "";

            if (cell.t === "d" || format.includes("yy") || format.includes("dd")) {
              try {
                const date = new Date(value);
                if (!isNaN(date.getTime())) value = date.toLocaleDateString("fr-FR");
              } catch {
                value = cell.v;
              }
            } else if (format.includes("%")) {
              value = (parseFloat(value) * 100).toFixed(2) + "%";
            } else if (typeof value === "number") {
              value = value.toLocaleString("fr-FR");
            }

            row.push(value ?? "");
          }
          data.push(row);
        }

        setExcelData(data);
      } else {
        alert("⚠️ Ce type de fichier n'est pas prévisualisable ici.");
      }
    } catch (err) {
      console.error(err);
      alert("❌ Erreur lors de la prévisualisation.");
    } finally {
      setPreviewLoading(false);
    }
  };

  // ===============================
  // 🔹 JSX principal
  // ===============================
  return (
    <div className="viewdata-overlay">
      <div className="viewdata-panel">
        <div className="viewdata-header">
          <h2>📊 Les données d’alimentations & System admin</h2>
          <button className="close-btn" onClick={onClose}>
            <FiX size={18} />
          </button>
        </div>
   <div
  className="data-type-buttons"
  style={{
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "12px",
  }}
>
  <button
  className="data-btn"
  onClick={() => {
    resetAll();
    handleLoadFiles("pdf");
  }}
>
  📄 Rapports PDF
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    handleLoadFiles("excel");
  }}
>
  📊 Fichiers Excel
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    handleLoadFiles("urls");
  }}
>
  
  🌐 URLs Scraping
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    handleLoadFiles("txt");
  }}
>
  📘 Training Data(Rapports) .txt
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    handleLoadFiles("json");
  }}
>
  📊 Training Data(Excels) .json
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    setShowIndicators(true);
  }}
>
  📦 Indicateurs
</button>

<button
  className="data-btn"
  onClick={() => {
    resetAll();
    setShowESAdmin(true);
  }}
>
  <SiElastic style={{ fontSize: "18px", marginRight: "6px" }} />
  ElasticSearch Management
</button>


</div>

        <div className="data-content">
          {!showIndicators && (
            <>
              {loading && <div className="loading">Chargement...</div>}

              {!loading && activeType && files.length === 0 && (
                <div className="empty">Aucun fichier trouvé pour ce type.</div>
              )}

{/* 🔥 BOUTON — DELETE ALL FILES 
{activeType && !showIndicators && !showESAdmin && (
  <div style={{ margin: "10px 0", textAlign: "right" }}>
    <button
      onClick={async () => {
  if (!activeType) {
    return alert("Sélectionne d'abord un type !");
  }

  const safeType = activeType.trim().toLowerCase();

  if (!safeType) {
    return alert("Type invalide");
  }

  if (
    !window.confirm(
      `⚠️ Supprimer TOUS les fichiers de type : ${safeType} ?`
    )
  ) {
    return;
  }

  try {
    const res = await deleteAllFiles(safeType);

    alert(`🗑️ Suppression terminée (${res.data.deleted} fichiers).`);

    setFiles([]);
    setExpandedFile(null);
    setPreviewUrl(null);
    setTextPreview(null);
    setExcelData(null);

  } catch (err) {
    console.error(err);
    alert("❌ Erreur lors de la suppression.");
  }


      }}
      style={{
        background: "#e53e3e",
        color: "#fff",
        padding: "6px 12px",
        borderRadius: "6px",
        display: "flex",
        alignItems: "center",
        gap: "6px",
        fontSize: "13px",
        cursor: "pointer",
        border: "none"
      }}
    >
     <FiTrash2 /> Supprimer tout 
    </button>
  </div>
)}

*/}


              {!loading && files.length > 0 && (
                <ul className="file-list scrollable-list">
                  {files.map((file) => (
                    <li key={file.id} className="file-card">
                      <div className="file-row">
                        <div className="file-main">
                          <div className="file-date">📅 {file.createdAt}</div>
                          <div className="file-name">{file.name}</div>
                        </div>

                        <div className="file-actions-horizontal">
                          {activeType !== "urls" && (
                            <>
                              <button title="Voir le fichier" onClick={() => handlePreview(file.id)}>
                                <FiEye />
                              </button>
                              <button title="Télécharger" onClick={() => handleDownload(file.id)}>
                                <FiDownload />
                              </button>
                            </>
                          )}

                          <button
                            title="Supprimer"
                            onClick={() => handleDelete(file.id)}
                            className="delete-btn"
                          >
                            <FiTrash2 />
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {showIndicators && <IndicatorsView />}
          {showESAdmin && <ESAdminDashboard />}
        </div>
      </div>

      {/* ✅ PDF / TXT / JSON / Excel Viewer reste inchangé */}
      {expandedFile && activeType === "pdf" && previewUrl && (
        <div className="pdf-fullscreen-overlay">
          <div className="pdf-toolbar">
            <button onClick={() => setExpandedFile(null)} className="close-pdf">
              ❌ Fermer
            </button>
          </div>
          <div className="pdf-viewer-container">
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
              <Viewer fileUrl={previewUrl} plugins={[defaultLayoutPluginInstance]} />
            </Worker>
          </div>
        </div>
      )}

      {expandedFile && (activeType === "txt" || activeType === "json") && textPreview && (
        <div className="text-viewer-overlay">
          <div className="text-toolbar">
            <button onClick={() => setExpandedFile(null)} className="close-pdf">
              ❌ Fermer
            </button>
          </div>
          <div className="text-viewer-container">
            {isJson ? (
              <pre
                className="json-preview-block"
                dangerouslySetInnerHTML={{ __html: syntaxHighlight(textPreview) }}
              />
            ) : (
              <pre className="txt-preview-block">{textPreview}</pre>
            )}
          </div>
        </div>
      )}

      {expandedFile && activeType === "excel" && excelData && (
        <div className="excel-viewer-overlay">
          <div className="excel-toolbar">
            <div style={{ flex: 1, display: "flex", gap: "10px" }}>
              <label>
                Zoom:
                <input
                  type="range"
                  min="50"
                  max="150"
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                />
                {zoom}%
              </label>
            </div>
            <button onClick={() => setExpandedFile(null)} className="close-pdf">
              ❌ Fermer
            </button>
          </div>

          <div className="excel-viewer-container">
            <div className="excel-scroll-wrapper">
              <table
                className="excel-preview-table"
                style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top left" }}
              >
                <thead>
                  <tr>
                    {excelData[0].map((cell, idx) => (
                      <th key={idx}>{cell ?? ""}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {excelData.slice(1).map((row, rowIndex) => (
                    <tr key={rowIndex} className={rowIndex % 2 === 0 ? "even-row" : "odd-row"}>
                      {row.map((cell, cellIndex) => {
                        let value = cell ?? "";
                        if (typeof value === "number" && value > 30000 && value < 60000) {
                          const date = XLSX.SSF.parse_date_code(value);
                          value = `${date.d}/${date.m}/${date.y}`;
                        }
                        return <td key={cellIndex}>{value}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {previewLoading && <div className="loading-overlay">Chargement du fichier...</div>}
    </div>
  );
}

// ===============================
// 🔹 Fonction syntaxHighlight JSON
// ===============================
function syntaxHighlight(json) {
  if (!json) return "";
  json = json.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|\b\d+\.?\d*\b)/g,
    (match) => {
      let cls = "json-number";
      if (/^"/.test(match)) cls = /:$/.test(match) ? "json-key" : "json-string";
      else if (/true|false/.test(match)) cls = "json-boolean";
      else if (/null/.test(match)) cls = "json-null";
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

// =========================================
// 🔹 Sous-composant IndicatorsView intégré
// =========================================
function IndicatorsView() {
  const [loading, setLoading] = useState(false);
  const [indicators, setIndicators] = useState([]);
  const [indicatorFiles, setIndicatorFiles] = useState([]);
  const [searchTermIndicators, setSearchTermIndicators] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 30;

//===============================
//🔥 SUPPRESSION — via service
//===============================

  const handleDeleteIndicator = async (id) => {
    if (!window.confirm("❌ Voulez-vous vraiment supprimer ce fichier indicateur ?")) return;

    try {
      await deleteIndicator(id);

      alert("🗑️ Fichier indicateur supprimé !");
      handleLoadIndicators(); // Refresh

    } catch (err) {
      console.error("Erreur suppression :", err);
      alert("❌ Impossible de supprimer ce fichier.");
    }
  };

  // ============================
  // 🔥 CHARGEMENT — via service
  // ============================
  const handleLoadIndicators = async () => {
    setLoading(true);
    setIndicators([]);
    setIndicatorFiles([]);

    try {
      const res = await fetchIndicatorsPrivate();
      setIndicators(Array.isArray(res?.data) ? res.data : []);
      setIndicatorFiles(Array.isArray(res?.files) ? res.files : []);
    } catch (err) {
      console.error("Erreur chargement indicateurs:", err);
      alert("❌ Impossible de charger les indicateurs.");
    } finally {
      setLoading(false);
    }
  };

  const normalizeText = (text) =>
    text
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "")
      .toLowerCase();

  const filteredIndicators = (Array.isArray(indicators) ? indicators : []).filter((item) =>
    normalizeText(item).includes(normalizeText(searchTermIndicators))
  );

  const totalPages = Math.ceil(filteredIndicators.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const currentItems = filteredIndicators.slice(startIndex, startIndex + itemsPerPage);

  const Pagination = () => (
    <div className="pagination">
      <button disabled={currentPage === 1} onClick={() => setCurrentPage((p) => p - 1)}>
        ⬅️
      </button>
      <span>
        {currentPage} / {totalPages || 1}
      </span>
      <button disabled={currentPage === totalPages} onClick={() => setCurrentPage((p) => p + 1)}>
        ➡️
      </button>
    </div>
  );

  return (
    <div style={{ height: "100vh", overflowY: "auto", padding: "10px" }}>
      <div className="indicators-section" style={{ width: "100%" }}>
        
        <h3>📦 Fichiers ({indicatorFiles.length})</h3>

        {indicatorFiles.length > 0 && (
          <ul className="file-list">
            {indicatorFiles.map((f, idx) => (
              <li
                key={idx}
                className="indicator-card"
                style={{
                  fontWeight: "bold",
                  color: "#cbd5e0",
                  fontSize: "13px",
                  background: "#1f2432",
                  border: "1px solid #2f3445",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>
                  <b>{f.filename}</b> — {f.total_indicators} indicateurs
                </span>

                {/* 🗑️ SUPPRESSION */}
                <span
                  onClick={() => handleDeleteIndicator(f.id)}
                  style={{
                    cursor: "pointer",
                    color: "red",
                    marginLeft: "10px",
                    fontSize: "18px",
                    fontWeight: "bold",
                  }}
                >
                  ✖
                </span>
              </li>
            ))}
          </ul>
        )}

        <div style={{ margin: "5px 0", fontWeight: "bold", color: "#cbd5e0" }}>
          Total indicateurs : {filteredIndicators.length}
        </div>

        <input
          type="text"
          placeholder="🔍 Rechercher un indicateur..."
          value={searchTermIndicators}
          onChange={(e) => {
            setSearchTermIndicators(e.target.value);
            setCurrentPage(1);
          }}
          className="search-input"
          style={{
            width: "100%",
            background: "#2a2e3c",
            color: "#cbd5e0",
            border: "1px solid #3a3f52",
          }}
        />

        {currentItems.length === 0 ? (
          <div className="empty">Aucun indicateur trouvé.</div>
        ) : (
          <ul className="file-list scrollable-list">
            {currentItems.map((item, idx) => (
              <li
                key={idx}
                className="indicator-card"
                style={{
                  fontWeight: "bold",
                  color: "#cbd5e0",
                  fontSize: "13px",
                  background: "#1f2432",
                  border: "1px solid #2f3445",
                }}
              >
                {typeof item === "string" ? item : JSON.stringify(item, null, 2)}
              </li>
            ))}
          </ul>
        )}

        <Pagination />

        <button onClick={handleLoadIndicators} style={{ marginTop: "10px" }}>
          🔄 Charger les indicateurs
        </button>
      </div>
    </div>
  );
}
