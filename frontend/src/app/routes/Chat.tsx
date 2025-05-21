import { useState, useEffect, useRef } from 'react';
import PromptInput from "../../components/PromptInput";
import '../../css/Chat.css';
import { auth } from '../../firebase/firebaseConfig';
import ReactMarkdown from 'react-markdown';

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
  title?: string; // Optional title from backend session
  messages: Message[];
}

const TYPING_SPEED = 15; // Milliseconds per character

// Define props for Chat component
interface ChatProps {
  currentSessionId: number | null;
  setCurrentSessionId: (id: number | null) => void;
  setRefreshSessionsTrigger: React.Dispatch<React.SetStateAction<number>>; // ADDED
}

export default function Chat({ currentSessionId, setCurrentSessionId, setRefreshSessionsTrigger }: ChatProps) { // MODIFIED
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false); // For prompt input disabling and backend loading
  const [error, setError] = useState<string | null>(null);
  const [currentUserUid, setCurrentUserUid] = useState<string | null>(null);
  
  const [messageToAnimate, setMessageToAnimate] = useState<Message | null>(null);
  const [typingMessageId, setTypingMessageId] = useState<number | null>(null);
  const [isNewMessageAnimating, setIsNewMessageAnimating] = useState<boolean>(false); // ADDED
  const messageListRef = useRef<HTMLDivElement>(null); // For scrolling

  // useEffect to scroll to the bottom of the message list
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages, typingMessageId]); // Scroll on new messages or during typing updates

  // Get current user UID
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(user => {
      if (user) {
        setCurrentUserUid(user.uid);
      } else {
        setCurrentUserUid(null);
        // Handle user not logged in (e.g., redirect to login or clear chat)
        setMessages([]);
        setCurrentSessionId(null); 
      }
    });
    return () => unsubscribe();
  }, [setCurrentSessionId]); // Added setCurrentSessionId to dependencies

  // useEffect to load session messages when currentSessionId changes or user changes
  useEffect(() => {
    if (isNewMessageAnimating) { // If a new message is currently animating, skip loading
      return;
    }
    if (currentSessionId && currentUserUid) {
      loadSessionMessages(currentSessionId);
    } else if (!currentSessionId) {
      // If currentSessionId is null (e.g., "New Chat"), clear messages
      setMessages([]);
      setMessageToAnimate(null); // Stop any animation
      setIsNewMessageAnimating(false); // ADDED: Ensure flag is cleared
      setError(null); // Clear any errors
    }
  }, [currentSessionId, currentUserUid, isNewMessageAnimating]); // Trigger when session ID, user UID, or animation flag changes // MODIFIED

  // useEffect to handle the typing animation
  useEffect(() => {
    if (!messageToAnimate || messageToAnimate.sender !== 'llm') {
      setTypingMessageId(null);
      // If messageToAnimate became null and we thought we were animating, reset flag.
      if (isNewMessageAnimating && !messageToAnimate) {
        setIsNewMessageAnimating(false);
      }
      return;
    }

    // At this point, messageToAnimate is valid and is an LLM message.
    // isNewMessageAnimating should be true if this animation was triggered by handleSendPrompt.

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
        // Ensure final content is set
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageToAnimate.id ? { ...msg, content: messageToAnimate.content } : msg
          )
        );
        // This will cause this effect to re-run and hit the top return block,
        // which will then call setIsNewMessageAnimating(false).
        setMessageToAnimate(null); 
      }
    }, TYPING_SPEED);

    return () => { // Cleanup when component unmounts or messageToAnimate changes
      clearInterval(intervalId);
      if (messageToAnimate) { 
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageToAnimate.id ? { ...msg, content: messageToAnimate.content } : msg
          )
        );
      }
      setTypingMessageId(null);
    };
  }, [messageToAnimate, isNewMessageAnimating]); // MODIFIED: Added isNewMessageAnimating dependency


  const handleSendPrompt = async (promptText: string) => {
    if (!promptText.trim() || isLoading || typingMessageId || !currentUserUid) {
      if (!currentUserUid) {
        setError("User not authenticated. Please login.");
        setIsLoading(false);
      }
      return;
    }

    setIsLoading(true);
    setError(null);

    const optimisticUserMessage: Message = {
      id: Date.now(), // Temporary ID
      sender: 'user',
      content: promptText,
      timestamp: new Date().toISOString(),
    };
    setMessages(prevMessages => [...prevMessages, optimisticUserMessage]);

    const apiUrl = import.meta.env.VITE_API_BASE_URL; // ADDED

    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (currentUserUid) {
        headers['X-User-Identifier'] = currentUserUid;
      }

      const response = await fetch(`${apiUrl}/chat/`, { // MODIFIED
        method: 'POST',
        headers: headers, // Use updated headers
        body: JSON.stringify({ 
          content: promptText, 
          session_id: currentSessionId // Use prop currentSessionId
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Failed to parse error response." }));
        setMessages(prevMessages => prevMessages.filter(msg => msg.id !== optimisticUserMessage.id));
        throw new Error(errData.detail || 'Failed to send message');
      }
      
      const data: ChatSessionResponse = await response.json();
      const newSessionCreated = !currentSessionId && data.id;
      setCurrentSessionId(data.id); // Update session ID from response (passed up to App.tsx)
      if (newSessionCreated) {
        setRefreshSessionsTrigger(prev => prev + 1); // ADDED: Trigger session list refresh
      }
      
      // Ensure backend messages adhere to the Message interface and IDs are numbers
      const backendMessages: Message[] = data.messages.map(m => ({
        id: Number(m.id), // Ensure ID is a number
        sender: m.sender || 'unknown', // Default if sender is missing
        content: m.content || '', // Default if content is missing
        timestamp: m.timestamp || new Date().toISOString(), // Default if timestamp is missing
      }));
      
      const lastMessageFromServer = backendMessages.length > 0 ? backendMessages[backendMessages.length - 1] : null;

      if (lastMessageFromServer && lastMessageFromServer.sender === 'llm') {
        // Last message is from LLM, prepare for animation.
        // Create a new array for UI display where the last LLM message content is initially empty.
        const messagesForUiDisplay = backendMessages.map(msg => 
          msg.id === lastMessageFromServer.id ? { ...msg, content: "" } : msg
        );
        setMessages(messagesForUiDisplay);
        setIsNewMessageAnimating(true); // ADDED: Signal animation is starting
        setMessageToAnimate(lastMessageFromServer); 
      } else {
        // No new LLM message to animate, or last message isn't from LLM, or no messages at all.
        // Simply set messages to the complete state from the backend.
        setMessages(backendMessages);
        setIsNewMessageAnimating(false); // ADDED: No animation, so clear flag
      }

    } catch (err: any) {
      setError(err.message || 'An unknown error occurred.');
      // Ensure optimistic message is removed if it wasn't replaced by a successful response.
      setMessages(prevMessages => prevMessages.filter(msg => msg.id !== optimisticUserMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  // Placeholder for fetching messages for a selected session
  const loadSessionMessages = async (sessionId: number) => {
    if (!currentUserUid) {
      setError("User not authenticated. Cannot load session.");
      setMessages([]); // Clear messages
      setMessageToAnimate(null); // ADDED
      setIsNewMessageAnimating(false); // ADDED
      return;
    }
    setIsLoading(true);
    setError(null);
    const apiUrl = import.meta.env.VITE_API_BASE_URL; // ADDED
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (currentUserUid) {
        headers['X-User-Identifier'] = currentUserUid;
      }
      // TODO: Construct the correct URL, e.g., /sessions/{sessionId}/messages
      // For now, assuming /sessions/{sessionId} returns the full session with messages
      const response = await fetch(`${apiUrl}/sessions/${sessionId}`, { // MODIFIED
        method: 'GET',
        headers: headers,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Failed to parse error response." }));
        // If session not found (e.g. 404), it might mean it's a new chat that hasn't been persisted yet
        // or an invalid ID. For now, treat as error.
        if (response.status === 404) {
            setError(`Session ${sessionId} not found.`);
            setMessages([]);
            setCurrentSessionId(null); // Reset session ID if not found
        } else {
            throw new Error(errData.detail || 'Failed to load session messages');
        }
        return; // Stop further processing
      }

      const data: ChatSessionResponse = await response.json();
      // setCurrentSessionId(data.id); // This is already set by the caller (Sidebar or initial load)
      const backendMessages: Message[] = data.messages.map(m => ({
        id: Number(m.id),
        sender: m.sender || 'unknown',
        content: m.content || '',
        timestamp: m.timestamp || new Date().toISOString(),
      }));
      setMessages(backendMessages);
      setMessageToAnimate(null); // Clear any ongoing animation from previous session
      setIsNewMessageAnimating(false); // ADDED: Ensure flag is cleared

    } catch (err: any) {
      setError(err.message || 'An unknown error occurred while loading session.');
      setMessages([]); // Clear messages on error
      setMessageToAnimate(null); // ADDED
      setIsNewMessageAnimating(false); // ADDED
    } finally {
      setIsLoading(false);
    }
  };
  // Note: You'll need to call loadSessionMessages when a session is selected from the sidebar.
  // For now, this function is just defined.

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
                  {msg.sender === 'llm' ? <ReactMarkdown>{msg.content}</ReactMarkdown> : msg.content}
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
