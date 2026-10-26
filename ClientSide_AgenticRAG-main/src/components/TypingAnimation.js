// src/components/TypingAnimation.js
import React from "react";
import Lottie from "lottie-react";
import typingAnimation from "../assets/typing.json"; // ajoute un JSON Lottie (typing indicator)

const TypingAnimation = () => {
  return (
    <div style={{ width: 60, height: 40 }}>
      <Lottie animationData={typingAnimation} loop={true} />
    </div>
  );
};

export default TypingAnimation;
// frontend_chatbot/src/components/MessageInput.js