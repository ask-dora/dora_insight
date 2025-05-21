import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faComments, faAtom, faGear, faCircleInfo, faUser,
  faChartBar, faPlus // Added faChartBar and faPlus
} from '@fortawesome/free-solid-svg-icons';
import { auth } from '../firebase/firebaseConfig';
import { signOut, onAuthStateChanged, type User } from 'firebase/auth';
import '../css/Sidebar.css';

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  user_id: number; // Or string, depending on your User model's ID type
}

interface SidebarProps {
  setCurrentSessionId: (id: number | null) => void;
  refreshSessionsTrigger: number; // ADDED
}

const Sidebar: React.FC<SidebarProps> = ({ setCurrentSessionId, refreshSessionsTrigger }) => { // MODIFIED
  const [user, setUser] = useState<User | null>(null);
  const [isLogoutMenuOpen, setIsLogoutMenuOpen] = useState(false);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(false);
  const [errorSessions, setErrorSessions] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        fetchChatSessions(currentUser.uid);
      } else {
        setChatSessions([]); // Clear sessions if user logs out
      }
    });
    return () => unsubscribe();
  }, [refreshSessionsTrigger]); // MODIFIED: Added refreshSessionsTrigger

  const fetchChatSessions = async (uid: string) => {
    setIsLoadingSessions(true);
    setErrorSessions(null);
    const apiUrl = import.meta.env.VITE_API_BASE_URL; // ADDED
    try {
      const response = await fetch(`${apiUrl}/users/${uid}/sessions/`, { // MODIFIED
        method: 'GET',
        headers: {
          'X-User-Identifier': uid,
        },
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Failed to fetch sessions."}));
        throw new Error(errData.detail || 'Failed to fetch chat sessions');
      }
      const data: ChatSession[] = await response.json();
      setChatSessions(data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())); // Sort by most recent
    } catch (error: any) {
      setErrorSessions(error.message);
      console.error("Error fetching chat sessions:", error);
    }
    setIsLoadingSessions(false);
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setIsLogoutMenuOpen(false);
      navigate('/login');
    } catch (error) {
      console.error("Error signing out: ", error);
    }
  };

  const toggleLogoutMenu = () => {
    setIsLogoutMenuOpen(!isLogoutMenuOpen);
  };

  const displayName = user?.displayName || user?.email || 'User';

  const handleNewChat = () => {
    setCurrentSessionId(null);
    navigate('/chat'); // Navigate to chat view for a new session
  };

  const handleSessionSelect = (sessionId: number) => {
    setCurrentSessionId(sessionId);
    navigate('/chat'); // Ensure chat view is active
  };

  return (
    <div className="sidebar expanded"> 
      <div className="sidebar-top-section"> {/* Wrapper for top content (title, new chat, nav links) */}
        <div className="sidebar-title-container">
          <h2 className="sidebar-title">Dora Insights</h2>
        </div>
        
        {/* New Chat Button - Moved up */}
        <div className="new-chat-button-container">
          <button onClick={handleNewChat} className="new-chat-button">
            <FontAwesomeIcon icon={faPlus} className="nav-icon" />
            <span className="nav-text">New Chat</span>
          </button>
        </div>

        {/* Static Navigation Links - Moved up */}
        <nav className="sidebar-nav static-nav-section">
          <ul className="static-nav-links">
            {/* Chat link removed as it's implicitly handled by sessions or new chat */}
            <li>
              <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faChartBar} className="nav-icon" />
                <span className="nav-text">Dashboard</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/integrations" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faAtom} className="nav-icon" />
                <span className="nav-text">Integrations</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faGear} className="nav-icon" />
                <span className="nav-text">Settings</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/help" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faCircleInfo} className="nav-icon" />
                <span className="nav-text">Help</span>
              </NavLink>
            </li>
          </ul>
        </nav>

        <hr className="sidebar-divider" /> {/* Divider */}

        {/* Chat Sessions List - Remains below divider */}
        <div className="chat-sessions-container">
          <p className="sessions-title">Recent Chats</p>
          {isLoadingSessions && <p className="loading-sessions">Loading...</p>}
          {errorSessions && <p className="error-sessions">Error: {errorSessions}</p>}
          {!isLoadingSessions && !errorSessions && chatSessions.length === 0 && (
            <p className="no-sessions">No chats yet.</p>
          )}
          <ul className="chat-sessions-list">
            {chatSessions.map(session => (
              <li key={session.id} className="session-item" onClick={() => handleSessionSelect(session.id)}>
                <FontAwesomeIcon icon={faComments} className="nav-icon session-icon" />
                <span className="nav-text session-title">{session.title || `Session ${session.id}`}</span>
              </li>
            ))}
          </ul>
        </div>
      </div> {/* End of sidebar-top-section */}

      {user && (
        <div className="sidebar-user-profile">
          <button onClick={toggleLogoutMenu} className="user-profile-button"> {/* Class simplified */}
            <FontAwesomeIcon icon={faUser} className="nav-icon user-icon" />
            <span className="nav-text user-name">{displayName}</span> {/* Always show text */}
            <span className="dropdown-arrow">{isLogoutMenuOpen ? '▲' : '▼'}</span> {/* Always show arrow */}
          </button>
          {isLogoutMenuOpen && ( // Condition simplified
            <div className="sidebar-logout-menu">
              <button onClick={handleLogout} className="sidebar-logout-item">
                Logout
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Sidebar;
