import React, { useContext } from 'react';
import axios from 'axios';
import { UserContext } from './UserContext';

const Logout = () => {
  const { logout } = useContext(UserContext);

  const handleLogout = async () => {
    try {
      await axios.post('http://localhost:8000/api/logout/');
      logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <div className="module">
      <h1>Logged out</h1>
      <p>You have been successfully logged out.</p>
      <button onClick={handleLogout}>Log Out</button>
    </div>
  );
};

export default Logout;
