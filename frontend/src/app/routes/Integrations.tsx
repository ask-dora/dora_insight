import React, { useState, useEffect } from 'react';
import { auth } from '../../firebase/firebaseConfig';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';
import '../../css/Integrations.css';

interface Integration {
  integration_type: string;
  is_connected: boolean;
  connected_at: string | null;
  integration_username: string | null;
}

interface IntegrationStatus {
  integrations: Integration[];
}

export default function Integrations() {
  const [user, setUser] = useState<User | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectingGitHub, setConnectingGitHub] = useState(false);

  const apiUrl = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        fetchIntegrations(currentUser.uid);
      } else {
        setIntegrations([]);
        setLoading(false);
      }
    });
    return () => unsubscribe();
  }, []);
  // Check for OAuth success/error in URL params
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const error = urlParams.get('error');

    console.log('URL params check - success:', success, 'error:', error, 'user:', user);

    if (success === 'github') {
      console.log('GitHub OAuth success detected, refreshing integrations...');
      // OAuth was successful, refresh integrations
      if (user) {
        fetchIntegrations(user.uid);
      }
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (error) {
      setError(`OAuth error: ${error}`);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [user]);
  const fetchIntegrations = async (uid: string) => {
    console.log('Fetching integrations for user:', uid);
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiUrl}/integrations/status`, {
        method: 'GET',
        headers: {
          'X-User-ID': uid,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch integrations: ${response.status}`);
      }

      const data: IntegrationStatus = await response.json();
      console.log('Fetched integrations data:', data);
      setIntegrations(data.integrations);
    } catch (err: any) {
      console.error('Error fetching integrations:', err);
      setError(err.message || 'Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  const connectGitHub = async () => {
    if (!user) {
      setError('Please log in to connect integrations');
      return;
    }

    setConnectingGitHub(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/integrations/auth/github/connect`, {
        method: 'GET',
        headers: {
          'X-User-ID': user.uid,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to initiate GitHub OAuth: ${response.status}`);
      }

      const data = await response.json();
      
      // Redirect to GitHub OAuth
      window.location.href = data.auth_url;
    } catch (err: any) {
      console.error('Error connecting to GitHub:', err);
      setError(err.message || 'Failed to connect to GitHub');
      setConnectingGitHub(false);
    }
  };

  const disconnectGitHub = async () => {
    if (!user) {
      setError('Please log in to manage integrations');
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/integrations/github`, {
        method: 'DELETE',
        headers: {
          'X-User-ID': user.uid,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to disconnect GitHub: ${response.status}`);
      }

      // Refresh integrations
      await fetchIntegrations(user.uid);
    } catch (err: any) {
      console.error('Error disconnecting GitHub:', err);
      setError(err.message || 'Failed to disconnect GitHub');
    }
  };
  const getGitHubIntegration = () => {
    const githubIntegration = integrations.find(integration => integration.integration_type === 'github');
    console.log('GitHub integration found:', githubIntegration);
    return githubIntegration;
  };
  if (!user) {
    return (
      <div className="integrations-container">
        <main className="integrations-main">
          <div className="integrations-content">
            <h1>Integrations</h1>
            <p className="login-message">Please log in to manage your integrations.</p>
          </div>
        </main>
      </div>
    );
  }
  return (
    <div className="integrations-container">
      <main className="integrations-main">
        <div className="integrations-content">          <h1>Integrations</h1>
          <p className="integrations-description">
            Connect your development tools and data sources to gain comprehensive insights into your software delivery performance.
          </p>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading integrations...</p>
            </div>
          ) : (
            <div className="integrations-grid">
              {/* GitHub Integration Card */}
              <div className="integration-card">
                <div className="integration-header">
                  <div className="integration-icon github-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                  </div>                  <div className="integration-info">
                    <h3>GitHub</h3>
                    <p>Connect your GitHub repositories to analyze deployment frequency, lead time, and failure recovery metrics</p>
                  </div>
                </div>
                
                <div className="integration-status">
                  {(() => {
                    const githubIntegration = getGitHubIntegration();
                    if (githubIntegration?.is_connected) {
                      return (
                        <div className="connected-state">
                          <div className="status-indicator connected">
                            <span className="status-dot"></span>
                            Connected as {githubIntegration.integration_username}
                          </div>
                          <p className="connected-date">
                            Connected on {new Date(githubIntegration.connected_at!).toLocaleDateString()}
                          </p>
                          <button 
                            onClick={disconnectGitHub}
                            className="disconnect-button"
                          >
                            Disconnect
                          </button>
                        </div>
                      );
                    } else {
                      return (
                        <div className="disconnected-state">
                          <div className="status-indicator disconnected">
                            <span className="status-dot"></span>
                            Not connected
                          </div>
                          <button 
                            onClick={connectGitHub}
                            disabled={connectingGitHub}
                            className="connect-button"
                          >
                            {connectingGitHub ? 'Connecting...' : 'Connect GitHub'}
                          </button>
                        </div>
                      );
                    }
                  })()}
                </div>
              </div>

              {/* Future integrations placeholder */}
              <div className="integration-card coming-soon">
                <div className="integration-header">
                  <div className="integration-icon gitlab-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.16l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.16l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
                    </svg>
                  </div>                  <div className="integration-info">
                    <h3>GitLab</h3>
                    <p>Coming soon - Connect your GitLab projects to track merge requests and deployments</p>
                  </div>
                </div>
                <div className="integration-status">
                  <div className="status-indicator coming-soon">
                    <span className="status-dot"></span>
                    Coming Soon
                  </div>
                </div>
              </div>

              <div className="integration-card coming-soon">
                <div className="integration-header">
                  <div className="integration-icon jira-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.78v1.7c0 2.4 1.94 4.34 4.34 4.34V2.84A.84.84 0 0121.16 2H11.53zM6.77 6.8c0 2.4 1.94 4.34 4.34 4.34h1.8v1.72c0 2.4 1.94 4.35 4.34 4.35V7.63a.83.83 0 00-.83-.83H6.77zM2 11.6c0 2.4 1.95 4.34 4.35 4.34h1.78v1.72c0 2.4 1.94 4.34 4.34 4.34V12.43a.83.83 0 00-.83-.83H2z"/>
                    </svg>
                  </div>                  <div className="integration-info">
                    <h3>Jira</h3>
                    <p>Coming soon - Connect your Jira projects to track issue resolution and deployment incidents</p>
                  </div>
                </div>
                <div className="integration-status">
                  <div className="status-indicator coming-soon">
                    <span className="status-dot"></span>
                    Coming Soon
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
