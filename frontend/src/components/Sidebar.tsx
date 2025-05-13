import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faComments, faAtom, faGear, faCircleInfo,
  faUser
} from '@fortawesome/free-solid-svg-icons';
import { auth } from '../firebase/firebaseConfig';
import { signOut, onAuthStateChanged, type User } from 'firebase/auth';
import '../css/Sidebar.css';

const Sidebar: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLogoutMenuOpen, setIsLogoutMenuOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, []);

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

  return (
    <div className="sidebar expanded"> {/* Always expanded */}
      <div> {/* Wrapper for top content (title, underline, and nav) */}
        <div className="sidebar-title-container">
          <h2 className="sidebar-title">Dora Insights</h2>
        </div>
        <nav className="sidebar-nav">
          <ul>
            <li>
              <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faComments} className="nav-icon" />
                <span className="nav-text">Chat / Dashboard</span> {/* Always show text */}
              </NavLink>
            </li>
            <li>
              <NavLink to="/integrations" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faAtom} className="nav-icon" />
                <span className="nav-text">Integrations</span> {/* Always show text */}
              </NavLink>
            </li>
            <li>
              <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faGear} className="nav-icon" />
                <span className="nav-text">Settings</span> {/* Always show text */}
              </NavLink>
            </li>
            <li>
              <NavLink to="/help" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                <FontAwesomeIcon icon={faCircleInfo} className="nav-icon" />
                <span className="nav-text">Help</span> {/* Always show text */}
              </NavLink>
            </li>
          </ul>
        </nav>
      </div>

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
