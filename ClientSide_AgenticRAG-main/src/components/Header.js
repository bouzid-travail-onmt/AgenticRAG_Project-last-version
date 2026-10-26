import React from "react";
import "../styles/Header.css";
import ministereLogo from "../assets/وزارة الإدماج الاقتصادي والمقاولة الصغرى والتشغيل والكفاءات.png";
import observatoireLogo from "../assets/logo_direction.jpg";

const Header = () => {
  return (
    <header className="app-header">
      {/* Logo gauche */}
      <div className="logo-section">
        <img
          src={ministereLogo}
          alt="Ministère"
          className="logo-ministere"
        />
      </div>

      {/* Logo droite */}
      <div className="logo-section">
        <img
          src={observatoireLogo}
          alt="Observatoire"
          className="logo-observatoire"
        />
      </div>
    </header>
  );
};

export default Header;
