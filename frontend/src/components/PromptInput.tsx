import { useState } from "react";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import '../css/PromptInput.css'; // Import the CSS file

export default function PromptInput() {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    console.log("Prompt:", prompt);
    // future: call MCP agent and update chart
  };

  return (
    <div className="prompt-input-container">
      <div className="prompt-input-bar"> {/* Added wrapper for input and button */}
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt here.." /* Changed placeholder */
          className="prompt-input-field"
        />
        <button
          className="prompt-submit-button"
          onClick={handleSubmit}
        >
          <FontAwesomeIcon icon={faPaperPlane} /> {/* Changed to icon */}
        </button>
      </div>
    </div>
  );
}
