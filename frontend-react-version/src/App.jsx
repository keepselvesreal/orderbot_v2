import React, { useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import Chat from './Chat';
import Order from './Order';
import { UserContext } from './UserContext';
import useWebSocket from './useWebSocket';


const App = () => {
  const { isAuthenticated, setIsAuthenticated, userId } = useContext(UserContext);
  const navigate = useNavigate();
  const { socketOpen, sendMessage, socket } = useWebSocket();


  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    navigate('/login');
  };

  const toggleLogin = () => {
    navigate('/login');
  };

  return (
    <div>
      <Navbar isAuthenticated={isAuthenticated} onLogout={handleLogout} onSignIn={toggleLogin} />
      <main className="container mt-4">
        <div className="row">
          <div className="col-md-8">
            <Chat socketOpen={socketOpen} sendMessage={sendMessage} socket={socket} />
          </div>
          <div className="col-md-4 d-flex flex-column align-items-center mt-md-5">
            <Order socketOpen={socketOpen} sendMessage={sendMessage} userId={userId} />
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;














