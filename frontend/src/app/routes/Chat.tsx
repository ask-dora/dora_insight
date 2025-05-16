import { useState, useEffect, useRef } from 'react'; // Added useRef
import PromptInput from "../../components/PromptInput";
import '../../css/Chat.css';

// Define a type for individual messages
interface Message {
  id: number;
  sender: string; // "user" or "llm"
  content: string;
  timestamp: string; // Assuming ISO string format from backend
}

// Define a type for the chat session response from the backend
interface ChatSessionResponse {
  id: number;
  created_at: string;
  messages: Message[];
}

const TYPING_SPEED = 15; // Milliseconds per character

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false); // For prompt input disabling and backend loading
  const [error, setError] = useState<string | null>(null);
  
  const [messageToAnimate, setMessageToAnimate] = useState<Message | null>(null);
  const [typingMessageId, setTypingMessageId] = useState<number | null>(null);
  const messageListRef = useRef<HTMLDivElement>(null); // For scrolling

  // useEffect to scroll to the bottom of the message list
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages, typingMessageId]); // Scroll on new messages or during typing updates

  // useEffect to handle the typing animation
  useEffect(() => {
    if (!messageToAnimate || messageToAnimate.sender !== 'llm') {
      setTypingMessageId(null);
      return;
    }

    setTypingMessageId(messageToAnimate.id);
    let currentText = "";
    let charIndex = 0;

    const intervalId = setInterval(() => {
      if (charIndex < messageToAnimate.content.length) {
        currentText += messageToAnimate.content[charIndex];
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageToAnimate.id ? { ...msg, content: currentText } : msg
          )
        );
        charIndex++;
      } else {
        clearInterval(intervalId);
        setTypingMessageId(null);
        // Ensure final content is set and clear the animation trigger
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageToAnimate.id ? { ...msg, content: messageToAnimate.content } : msg
          )
        );
        setMessageToAnimate(null); 
      }
    }, TYPING_SPEED);

    return () => { // Cleanup when component unmounts or messageToAnimate changes
      clearInterval(intervalId);
      if (messageToAnimate) { // If animation was interrupted, set full content
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageToAnimate.id ? { ...msg, content: messageToAnimate.content } : msg
          )
        );
      }
      setTypingMessageId(null);
    };
  }, [messageToAnimate]); // Dependency: messageToAnimate


  const handleSendPrompt = async (promptText: string) => {
    if (!promptText.trim() || isLoading || typingMessageId) return;

    setIsLoading(true);
    setError(null);

    const optimisticUserMessage: Message = {
      id: Date.now(), // Temporary ID
      sender: 'user',
      content: promptText,
      timestamp: new Date().toISOString(),
    };
    setMessages(prevMessages => [...prevMessages, optimisticUserMessage]);

    try {
      const response = await fetch('http://localhost:8000/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: promptText, session_id: currentSessionId }),
      });

      if (!response.ok) {
        // If response is not OK, parse the error response separately
        const errData = await response.json().catch(() => ({ detail: "Failed to parse error response." }));
        setMessages(prevMessages => prevMessages.filter(msg => msg.id !== optimisticUserMessage.id));
        throw new Error(errData.detail || 'Failed to send message');
      }
      
      // If response is OK, parse the success response
      const data: ChatSessionResponse = await response.json();
      setCurrentSessionId(data.id);
      const backendMessages = data.messages.map(m => ({...m, id: Number(m.id)}));
      const lastMessageFromServer = backendMessages.length > 0 ? backendMessages[backendMessages.length - 1] : null;

      if (lastMessageFromServer && lastMessageFromServer.sender === 'llm') {
        const existingMessage = messages.find(m => m.id === lastMessageFromServer.id);
        if (!existingMessage || existingMessage.content !== lastMessageFromServer.content || existingMessage.id === optimisticUserMessage.id) {
          // Remove optimistic user message before setting backend messages
          const messagesWithoutOptimistic = messages.filter(msg => msg.id !== optimisticUserMessage.id);
          
          setMessages([...messagesWithoutOptimistic, ...backendMessages.map(m => {
            if (m.id === lastMessageFromServer.id) {
              return {...m, content: ""}; // Prepare for typing
            }
            return m;
          })]);
          setMessageToAnimate(lastMessageFromServer);
        } else {
          setMessages(backendMessages); // No animation needed
        }
      } else {
         // No new LLM message, or last message isn't LLM.
         // Replace optimistic message with confirmed messages.
        const messagesWithoutOptimistic = messages.filter(msg => msg.id !== optimisticUserMessage.id);
        setMessages([...messagesWithoutOptimistic, ...backendMessages]);
      }

    } catch (err: any) {
      setError(err.message || 'An unknown error occurred.');
      // Ensure optimistic message is removed if not already handled
      setMessages(prevMessages => prevMessages.filter(msg => msg.id !== optimisticUserMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <main className="chat-main">
        <div className="message-list" ref={messageListRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row message-${msg.sender}`}>
              <div className={`message-avatar-${msg.sender === 'llm' ? 'llm' : 'user'}`}></div>
              <div className="message-bubble">
                <div className="message-sender-name">{msg.sender === 'llm' ? 'Dora Bot' : 'You'}</div>
                <div
                  className={`message-content ${msg.sender === 'llm' && typingMessageId === msg.id ? 'is-typing' : ''}`}
                >
                  {msg.content}
                </div>
                <div className="message-timestamp">{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
              </div>
            </div>
          ))}
          {isLoading && !typingMessageId && !messages.some(m=> m.sender === 'llm' && m.id === typingMessageId) &&
            <div className="message-row message-llm">
              <div className="message-avatar-llm"></div>
              <div className="message-bubble">
                <div className="message-sender-name">Dora Bot</div>
                <div className="message-content is-typing">Thinking...</div>
              </div>
            </div>
          }
          {error && 
            <div className="message-row message-system">
               <div className="message-bubble message-error-bubble">
                Error: {error}
              </div>
            </div>
          }
        </div>
      </main>
      <div className="prompt-input-wrapper">
        <PromptInput
            onSendPrompt={handleSendPrompt}
            disabled={isLoading || !!typingMessageId}
        />
      </div>
    </div>
  );
}
