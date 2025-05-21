// src/app/routes/Login.tsx

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { signInWithEmailAndPassword, sendPasswordResetEmail, createUserWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from 'firebase/auth';
import type { User } from 'firebase/auth';
import { auth } from '../../firebase/firebaseConfig'; // Adjusted path
import '../../css/Login.css'; // Adjusted path

// Function to ensure user exists in our backend
const syncUserWithBackend = async (firebaseUser: User) => {
  if (!firebaseUser || !firebaseUser.uid) {
    console.error("Firebase user or UID is missing for backend sync.");
    return;
  }
  const userIdentifier = firebaseUser.uid;
  const apiUrl = import.meta.env.VITE_API_BASE_URL; // ADDED

  try {
    // We can call the endpoint to list sessions. This will implicitly create the user if not present.
    // Or, you could have a dedicated POST /users/sync endpoint.
    const response = await fetch(`${apiUrl}/users/${userIdentifier}/sessions/`, { // MODIFIED
      method: 'GET', // Or POST to a sync endpoint
      headers: {
        'X-User-Identifier': userIdentifier,
        // Potentially include Firebase ID token for backend verification if needed in future
        // 'Authorization': `Bearer ${await firebaseUser.getIdToken()}`,
      },
    });
    if (!response.ok) {
      // Handle cases where the backend might return an error even if user creation is attempted
      const errorData = await response.json().catch(() => (null)); // Catch if error response is not JSON
      console.error("Failed to sync user with backend", response.status, errorData);
      // Depending on the error, you might want to inform the user or retry
    } else {
      console.log("User synced/verified with backend successfully.");
      // Optionally, you could fetch user details from your backend here if needed immediately
    }
  } catch (error) {
    console.error("Error syncing user with backend:", error);
  }
};

// Google Logo SVG component (remains as previously defined, or can be imported if it's a separate .svg file)
const GoogleLogo = () => (
    <svg style={{ marginRight: '0.5rem' }} width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.6402 9.20455C17.6402 8.60227 17.583 8.00909 17.4787 7.43636H9V10.8182H13.8448C13.6366 11.9705 13.0002 12.9227 12.048 13.5636V15.8193H14.9562C16.6582 14.2523 17.6402 11.9318 17.6402 9.20455Z" fill="#4285F4"/>
        <path d="M9.00001 18C11.4307 18 13.4682 17.1932 14.9562 15.8193L12.048 13.5636C11.2568 14.1023 10.2261 14.4318 9.00001 14.4318C6.65569 14.4318 4.6716 12.8182 3.96478 10.6818H0.957962V12.9955C2.43864 15.9659 5.48183 18 9.00001 18Z" fill="#34A853"/>
        <path d="M3.96478 10.6818C3.78637 10.1341 3.68182 9.57045 3.68182 9C3.68182 8.42955 3.78637 7.86591 3.96478 7.31818V5.00455H0.957962C0.347732 6.17045 0 7.54545 0 9C0 10.4545 0.347732 11.8295 0.957962 12.9955L3.96478 10.6818Z" fill="#FBBC05"/>
        <path d="M9.00001 3.56818C10.3216 3.56818 11.5079 4.02273 12.4784 4.93182L15.0284 2.38636C13.4602 0.909091 11.4227 0 9.00001 0C5.48183 0 2.43864 2.03409 0.957962 5.00455L3.96478 7.31818C4.6716 5.18182 6.65569 3.56818 9.00001 3.56818Z" fill="#EA4335"/>
    </svg>
);

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // const [rememberMe, setRememberMe] = useState(false); // Removed
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [isSignUp, setIsSignUp] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (user: User | null) => { // made async
      if (user) {
        await syncUserWithBackend(user); // Sync user with backend
        navigate('/chat'); // Navigate to chat after sync
      } else {
        // User is signed out
        // Potentially clear any stored user identifier here
      }
    });
    return unsubscribe;
  }, [navigate]);

  const handleEmailPasswordLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // syncUserWithBackend will be called by onAuthStateChanged
    } catch (err: any) {
      console.error('Email/password login error', err);
      if (err.code === 'auth/invalid-credential' || err.code === 'auth/user-not-found' || err.code === 'auth/wrong-password' || err.code === 'auth/invalid-email') {
        setError('Invalid email or password. Please try again.');
      } else {
        setError(err.message || 'Failed to sign in. Please try again.');
      }
    }
  };

  const handleGoogleSignIn = async () => {
    setError(null);
    setMessage(null);
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
      // syncUserWithBackend will be called by onAuthStateChanged
    } catch (err: any) {
      console.error('Google sign-in error', err);
      setError(err.message || 'Failed to sign in with Google. Please try again.');
    }
  };

  const handlePasswordReset = async () => {
    if (!email && !isSignUp) {
      setError('Please enter your email address in the email field to reset your password.');
      return;
    }
    const emailToReset = isSignUp ? newEmail : email;
    if (!emailToReset) {
        setError('Please enter an email address to reset your password.');
        return;
    }
    setError(null);
    setMessage(null);
    try {
      await sendPasswordResetEmail(auth, emailToReset);
      setMessage('Password reset email sent! Check your inbox.');
    } catch (err: any) {
      console.error('Password reset error', err);
      setError(err.message || 'Failed to send password reset email.');
    }
  };
  
  const handleSignUp = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    try {
      await createUserWithEmailAndPassword(auth, newEmail, newPassword);
      // syncUserWithBackend will be called by onAuthStateChanged
      setIsSignUp(false);
      setNewEmail('');
      setNewPassword('');
      setConfirmPassword('');
      setMessage('Account created successfully! Please sign in.');
    } catch (err: any) {
      console.error('Sign up error', err);
      if (err.code === 'auth/email-already-in-use') {
        setError('This email address is already in use.');
      } else if (err.code === 'auth/weak-password') {
        setError('Password is too weak. It should be at least 6 characters.');
      } else {
        setError(err.message || 'Failed to create an account. Please try again.');
      }
    }
  };

  const commonFormElements = (isSignUpForm: boolean) => (
    <>
      {error && <p className="error-message">{error}</p>}
      {message && <p className="message-text">{message}</p>}

      <form onSubmit={isSignUpForm ? handleSignUp : handleEmailPasswordLogin} className="form-main">
        <div>
          <label htmlFor={isSignUpForm ? "new-email" : "email"} className="label">
            Email address
          </label>
          <input
            id={isSignUpForm ? "new-email" : "email"}
            name={isSignUpForm ? "new-email" : "email"}
            type="email"
            autoComplete="email"
            required
            value={isSignUpForm ? newEmail : email}
            onChange={(e) => isSignUpForm ? setNewEmail(e.target.value) : setEmail(e.target.value)}
            className="input-field"
          />
        </div>

        <div>
          <label htmlFor={isSignUpForm ? "new-password" : "password"} className="label">
            Password
          </label>
          <input
            id={isSignUpForm ? "new-password" : "password"}
            name={isSignUpForm ? "new-password" : "password"}
            type="password"
            autoComplete={isSignUpForm ? "new-password" : "current-password"}
            required
            value={isSignUpForm ? newPassword : password}
            onChange={(e) => isSignUpForm ? setNewPassword(e.target.value) : setPassword(e.target.value)}
            className="input-field"
          />
        </div>

        {isSignUpForm && (
          <div>
            <label htmlFor="confirm-password" className="label">
              Confirm Password
            </label>
            <input
              id="confirm-password"
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-field"
            />
          </div>
        )}

        {!isSignUpForm && (
          <div className="checkbox-section">
            {/* Remember me checkbox removed */}
            <div className="forgot-password-container" style={{ width: '100%', textAlign: 'right' }}> {/* Adjusted to take full width and align right */}
              <button
                type="button"
                onClick={handlePasswordReset}
                className="forgot-password-button"
              >
                Forgot password?
              </button>
            </div>
          </div>
        )}

        <div>
          <button
            type="submit"
            className="submit-button"
          >
            {isSignUpForm ? 'Sign Up' : 'Sign in'}
          </button>
        </div>
      </form>

      {!isSignUpForm && (
        <>
          <div className="divider-container">
            <div className="divider-relative">
              <div className="divider-absolute-center">
                <div className="divider-line" />
              </div>
              <div className="divider-text-wrapper">
                <span className="divider-text">Or</span>
              </div>
            </div>
          </div>

          <div className="google-signin-button-container">
            <button
              type="button"
              onClick={handleGoogleSignIn}
              className="google-signin-button"
            >
              <GoogleLogo />
              Sign in with Google
            </button>
          </div>
        </>
      )}
      
      <div className="toggle-auth-container">
        {isSignUpForm ? 'Already have an account?' : "Don't have an account?"}{' '}
        <button 
          onClick={() => { 
            setIsSignUp(!isSignUpForm); 
            setError(null); 
            setMessage(null); 
            setEmail(''); setPassword(''); setNewEmail(''); setNewPassword(''); setConfirmPassword('');
          }} 
          className="toggle-auth-button"
        >
          {isSignUpForm ? 'Sign in' : 'Sign up'}
        </button>
      </div>
    </>
  );


  return (
    <div className="login-page-container">
      {/* Left Side: Form Panel */}
      <div className="form-panel">
        <div className="logo-container">
          <div className="logo-icon"></div>
          <span className="logo-text">Dora Insights</span> {/* Changed logo text */}
        </div>

        <div className="form-content-wrapper">
          {isSignUp ? (
            <>
              <h2 className="form-title">Create Account</h2>
              <p className="form-subtitle">Get started with Dora Insights.</p> {/* Changed text */}
              {commonFormElements(true)}
            </>
          ) : (
            <>
              <h1 className="form-title">Welcome back</h1>
              <p className="form-subtitle">Please enter your details</p>
              {commonFormElements(false)}
            </>
          )}
        </div>
      </div>

      {/* Right Side: Image Panel (Keep structure, CSS will hide/show) */}
      {/* <div className="image-panel"> */}
      {/*   <img src="/path-to-your-illustration.svg" alt="Illustration" className="illustration-image" /> */}
      {/* </div> */}
    </div>
  );
}
