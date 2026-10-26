import React from "react";

export default function NotFound() {
return (
<div style={{ padding: "40px", textAlign: "center", color: "white" }}>
<h1>404 - Page Introuvable</h1>
<p>Cette page n'existe pas ou a été déplacée.</p>
<a href="/" style={{ color: "#4dabf7", textDecoration: "underline" }}>Retour à l'accueil</a>
</div>
);
}