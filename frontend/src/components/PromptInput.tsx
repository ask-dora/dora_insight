import { useState } from "react";
import type { KeyboardEvent } from "react"; // Correct type-only import for KeyboardEvent
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import '../css/PromptInput.css';

interface PromptInputProps {
  onSendPrompt: (promptText: string) => void;
  disabled?: boolean;
}

export default function PromptInput({ onSendPrompt, disabled = false }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    const trimmedPrompt = prompt.trim();
    if (trimmedPrompt && !disabled) {
      onSendPrompt(trimmedPrompt);
      setPrompt(""); // Clear input after sending
      // Reset textarea height after clearing
      const textarea = document.querySelector('.prompt-input-field') as HTMLTextAreaElement;
      if (textarea) {
        textarea.style.height = 'auto'; // Reset to auto to shrink if needed
      }
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="prompt-input-container">
      <div className="prompt-input-bar">
        <textarea
          value={prompt}
          onChange={(e) => {
            setPrompt(e.target.value);
            // Auto-resize logic
            e.target.style.height = 'auto';
            e.target.style.height = `${e.target.scrollHeight}px`;
          }}
          onKeyDown={handleKeyDown}
          placeholder="Enter your prompt here.."
          className="prompt-input-field"
          rows={1}
          style={{ resize: 'none', overflowY: 'hidden' }} // Ensure overflowY is hidden for auto-resize
          disabled={disabled}
        />
        <button
          className="prompt-submit-button"
          onClick={handleSubmit}
          disabled={disabled}
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </div>
    </div>
  );
}
