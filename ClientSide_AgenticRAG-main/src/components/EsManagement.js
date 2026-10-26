// src/components/EsManagement.js
import React, { useState, useEffect } from "react";
import {
  FiTrash2,
  FiSearch,
  FiFilter,
  FiXCircle,
  FiDatabase
} from "react-icons/fi";
import {
  fetchDocuments,
  deleteDocument,
  deleteAllDocuments
} from "../services/ViewDataService";

export default function ESAdminDashboard() {
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [indicator, setIndicator] = useState("");
  const [year, setYear] = useState("");
  const [filename, setFilename] = useState("");

  const pageSizes = Array.from({ length: Math.ceil(10000 / 100) }, (_, i) => (i + 1) * 100).filter(s => s <= 10000);
  const [pageSize, setPageSize] = useState(30);

  const loadData = async () => {
    setLoading(true);

    const data = await fetchDocuments({
      indicator,
      year,
      filename,
      size: pageSize
    });

    setDocuments(data.items || []);
    setTotal(data.total || 0);

    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (id) => {
    await deleteDocument(id);
    loadData();
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Supprimer TOUTES les données ElasticSearch ?")) return;
    await deleteAllDocuments();
    loadData();
  };

  return (
    <div style={{ height: "100vh", overflowY: "auto", padding: "10px" }}>

      {/* 🟦 HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <h2 style={{ fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
          <FiDatabase /> ElasticSearch Admin
        </h2>

        <button
          onClick={handleDeleteAll}
          style={{
            background: "#e53e3e",
            color: "#fff",
            padding: "4px 8px",
            borderRadius: "6px",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "12px",
            cursor: "pointer"
          }}
        >
          <FiTrash2 /> Supprimer tout
        </button>
      </div>

      {/* 🟧 FILTRES */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px", background: "#2a2e3c", padding: "6px", borderRadius: "6px" }}>
        <input
          placeholder="Indicator"
          value={indicator}
          onChange={(e) => setIndicator(e.target.value)}
          style={{ flex: 1, padding: "4px", borderRadius: "4px", border: "1px solid #3a3f52", fontSize: "12px", background: "#1f2432", color: "#cbd5e0" }}
        />
        <input
          placeholder="Année"
          value={year}
          onChange={(e) => setYear(e.target.value)}
          style={{ flex: 1, padding: "4px", borderRadius: "4px", border: "1px solid #3a3f52", fontSize: "12px", background: "#1f2432", color: "#cbd5e0" }}
        />
        <input
          placeholder="Filename"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          style={{ flex: 1, padding: "4px", borderRadius: "4px", border: "1px solid #3a3f52", fontSize: "12px", background: "#1f2432", color: "#cbd5e0" }}
        />
        <select
          value={pageSize}
          onChange={(e) => setPageSize(Number(e.target.value))}
          style={{ padding: "4px", borderRadius: "4px", border: "1px solid #3a3f52", fontSize: "12px", background: "#1f2432", color: "#cbd5e0" }}
        >
          {pageSizes.map((s) => (
            <option key={s} value={s}>{s} / page</option>
          ))}
        </select>
        <button
          onClick={loadData}
          style={{ background: "#3182ce", color: "#fff", padding: "4px 8px", borderRadius: "6px", display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", cursor: "pointer" }}
        >
          <FiSearch /> Rechercher
        </button>
      </div>

      {/* 🟩 TOTAL */}
      <div style={{ marginBottom: "6px", fontWeight: "bold", fontSize: "12px", color: "#cbd5e0" }}>
        Total documents : {total}
      </div>

      {/* 🟦 GRID DOCUMENTS scrollable */}
      <div style={{ maxHeight: "70vh", overflowY: "auto", background: "#1f2432", borderRadius: "8px", padding: "6px" }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: "8px", fontSize: "12px", color: "#cbd5e0" }}>Chargement...</div>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "8px", fontSize: "12px", color: "#cbd5e0" }}>Aucun document trouvé.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
            {documents.map((doc) => (
              <li
                key={doc._id}
                style={{
                  padding: "6px",
                  background: "#2a2e3c",
                  borderRadius: "6px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "2px",
                  fontSize: "12px"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ fontWeight: "bold", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{doc.indicator}</h3>
                  <FiXCircle
                    style={{ color: "#e53e3e", cursor: "pointer" }}
                    size={16}
                    onClick={() => handleDelete(doc._id)}
                  />
                </div>
                <p style={{ fontSize: "10px", color: "#cbd5e0" }}>📅 {doc.year}</p>
                <p style={{ fontSize: "10px", color: "#cbd5e0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>📄 {doc.filename}</p>
                <p style={{ fontSize: "10px", fontWeight: "bold", marginTop: "2px", color: "#cbd5e0" }}>Valeur : {doc.value}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
