import { useState } from "react";
import '../css/PromptInput.css'; // Import the CSS file

export default function PromptInput() {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    console.log("Prompt:", prompt);
    // future: call MCP agent and update chart
  };

  return (
    <div className="prompt-input-container"> {/* Replaced mb-4 */}
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the chart you want..."
        className="prompt-input-field" /* Replaced w-full border px-4 py-2 rounded-md */
      />
      <button
        className="prompt-submit-button" /* Replaced mt-2 bg-blue-500 text-white px-4 py-2 rounded-md */
        onClick={handleSubmit}
      >
        Generate Chart
      </button>
    </div>
  );
}
