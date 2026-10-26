// src/components/Login.js
import React, { useState } from "react";
import { FiUser, FiLock } from "react-icons/fi";
import "../styles/Login.css";
import { login } from "../services/loginService";

export default function Login({ onClose, onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const validateEmail = (email) => {
    if (!email.includes("@")) return "L'adresse email doit contenir @";
    if (!email.endsWith("emploi.gov.ma")) return "L'adresse doit appartenir au domaine emploi.gov.ma";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const validationError = validateEmail(username);
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      const res = await login(username, password);
      console.log("✅ Connexion réussie :", res);
      onSuccess && onSuccess();
      onClose();
    } catch (err) {
      console.error("Erreur login:", err);
      let message = "Échec de la connexion";
      if (err.detail) {
        if (Array.isArray(err.detail)) message = err.detail[0]?.msg || message;
        else if (typeof err.detail === "string") message = err.detail;
      }
      setError(message);
    }
  };

  return (
    <div className="login-overlay">
      <div className="login-container">
        <h2 className="login-title">Portail d’authentification</h2>
        <p className="login-subtitle">Accès réservé aux administrateurs</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <FiUser className="icon" />
            <input
              type="text"
              placeholder="Adresse email (emploi.gov.ma)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <FiLock className="icon" />
            <input
              type="password"
              placeholder="Mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <button type="submit" className="btn-login">Se connecter</button>
          <button type="button" className="btn-close" onClick={onClose}>Annuler</button>
        </form>
      </div>
    </div>
  );
}
