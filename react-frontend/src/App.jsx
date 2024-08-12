import React, { useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import Chat from './Chat';
import Order from './Order';
import { UserContext } from './UserContext';
import { WebSocketProvider } from './useWebSocket';

const App = () => {
  const { isAuthenticated, refreshUser, logout } = useContext(UserContext);
  const navigate = useNavigate();

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleLogin = () => {
    navigate('/login');
  };

  return (
    <WebSocketProvider>
      <div>
        <Navbar isAuthenticated={isAuthenticated} onLogout={handleLogout} onSignIn={toggleLogin} />
        <main className="container mt-4">
          <div className="row">
            <div className="col-md-8">
              <Chat />
            </div>
            <div className="col-md-4 d-flex flex-column align-items-center mt-md-5">
              <Order />
            </div>
          </div>
        </main>
      </div>
    </WebSocketProvider>
  );
};

export default App;
