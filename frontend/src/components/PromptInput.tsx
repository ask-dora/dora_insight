import { useState } from "react";

export default function PromptInput() {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    console.log("Prompt:", prompt);
    // future: call MCP agent and update chart
  };

  return (
    <div className="mb-4">
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the chart you want..."
        className="w-full border px-4 py-2 rounded-md"
      />
      <button
        className="mt-2 bg-blue-500 text-white px-4 py-2 rounded-md"
        onClick={handleSubmit}
      >
        Generate Chart
      </button>
    </div>
  );
}
