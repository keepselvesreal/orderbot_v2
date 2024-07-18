import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

const UserContext = createContext();

const UserProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [userId, setUserId] = useState(null);
 

  useEffect(() => {
    const fetchCurrentUser = async () => {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        console.error('No access token found.');
        return;
      }

      try {
        const response = await axios.get('http://127.0.0.1:8000/api/user/', {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.status === 200) {
          const data = response.data;
          setIsAuthenticated(true);
          setUser(data);
          setUserId(data.id);
        } else if (response.status === 401) {
          console.error('Unauthorized access. Redirecting to login.');
          setIsAuthenticated(false);
          setUserId(null);
        } else {
          console.error('Failed to fetch current user.');
          setIsAuthenticated(false);
          setUserId(null);
        }
      } catch (error) {
        console.error('Error fetching current user:', error);
      }
    };

    fetchCurrentUser();
  }, []);

  return (
    <UserContext.Provider value={{ isAuthenticated, userId, user, setIsAuthenticated, setUserId, setUser }}>
      {children}
    </UserContext.Provider>
  );
};

export { UserContext, UserProvider };


