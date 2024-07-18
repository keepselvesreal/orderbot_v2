import React from 'react';
import axios from 'axios';

const Logout = ({ setLoggedIn }) => {
  const handleLogout = async () => {
    try {
      await axios.post('http://localhost:8000/api/logout/');
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setLoggedIn(false);
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
