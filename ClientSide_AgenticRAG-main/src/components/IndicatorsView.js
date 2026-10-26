import React, { useState, useEffect } from "react";
import { fetchIndicatorsPublic } from "../services/ViewDataService";

function IndicatorsView() {
  const [loading, setLoading] = useState(false);
  const [indicators, setIndicators] = useState([]);
  const [searchTermIndicators, setSearchTermIndicators] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  // Charger automatiquement les indicateurs au montage
  useEffect(() => {
    loadIndicators();
  }, []);

  const loadIndicators = async () => {
    setLoading(true);
    try {
      const res = await fetchIndicatorsPublic();
      const indicatorsList = Array.isArray(res?.data) ? res.data : [];
      setIndicators(indicatorsList);
    } catch (err) {
      console.error("Erreur chargement indicateurs:", err);
      alert("❌ Impossible de charger les indicateurs.");
    } finally {
      setLoading(false);
    }
  };

  // Normalisation texte pour une recherche pertinente
  const normalizeText = (text) =>
    text
      ?.toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "")
      .toLowerCase();

  // Filtrage intelligent
  const filteredIndicators = (Array.isArray(indicators) ? indicators : []).filter((item) =>
    normalizeText(item).includes(normalizeText(searchTermIndicators))
  );

  // Pagination
  const totalPages = Math.ceil(filteredIndicators.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const currentItems = filteredIndicators.slice(startIndex, startIndex + itemsPerPage);

  const Pagination = () => (
    <div className="pagination" style={{ marginTop: "10px", textAlign: "center" }}>
      <button
        disabled={currentPage === 1}
        onClick={() => setCurrentPage((p) => p - 1)}
        style={{
          padding: "4px 8px",
          marginRight: "10px",
          cursor: currentPage === 1 ? "not-allowed" : "pointer",
        }}
      >
        ⬅️
      </button>
      <span style={{ color: "#cbd5e0" }}>
        {currentPage} / {totalPages || 1}
      </span>
      <button
        disabled={currentPage === totalPages}
        onClick={() => setCurrentPage((p) => p + 1)}
        style={{
          padding: "4px 8px",
          marginLeft: "10px",
          cursor: currentPage === totalPages ? "not-allowed" : "pointer",
        }}
      >
        ➡️
      </button>
    </div>
  );

  return (
    <div style={{ height: "100vh", overflowY: "auto", padding: "10px" }}>
      <div className="indicators-section" style={{ width: "100%" }}>
        {/* Barre de recherche */}
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
            padding: "8px",
            borderRadius: "5px",
            marginBottom: "10px",
          }}
        />

        {/* Liste paginée */}
        {loading ? (
          <div style={{ color: "#cbd5e0" }}>⏳ Chargement...</div>
        ) : currentItems.length === 0 ? (
          <div className="empty" style={{ color: "#cbd5e0" }}>
            Aucun indicateur trouvé.
          </div>
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
      </div>
    </div>
  );
}

export default IndicatorsView;
