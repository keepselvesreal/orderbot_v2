import React, { createContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom'; 

const UserContext = createContext();

const UserProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [userId, setUserId] = useState(null);
  const navigate = useNavigate();


  const fetchCurrentUser = useCallback(async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      console.error('No access token found.');
      navigate("/login");
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
        if (data.id !== userId || !isAuthenticated) {
          setIsAuthenticated(true);
          setUser(data);
          setUserId(data.id);
        }
      } else if (response.status === 401) {
        console.error('Unauthorized access. Redirecting to login.');
        setIsAuthenticated(false);
        setUser(null);
        setUserId(null);
        navigate("/login");
      } else {
        console.error('Failed to fetch current user.');
        setIsAuthenticated(false);
        setUser(null);
        setUserId(null);
      }
    } catch (error) {
      console.error('Error fetching current user:', error);
      setIsAuthenticated(false);
      setUser(null);
      setUserId(null);
    }
  }, [isAuthenticated, userId, navigate]);


  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);


  const login = async (username, password) => {
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/token/', {
        username,
        password
      });

      localStorage.setItem('accessToken', response.data.access);
      setIsAuthenticated(true);
      setUser(response.data.user);
      setUserId(response.data.user.id);
    } catch (error) {
      console.error('Login error:', error);
      setIsAuthenticated(false);
      setUser(null);
      setUserId(null);
    }
  };


  const logout = () => {
    localStorage.removeItem('accessToken');
    setIsAuthenticated(false);
    setUser(null);
    setUserId(null);
  };


  const refreshUser = useCallback(async () => {
    try {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        console.error('No access token found.');
        return;
      }

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
        setUser(null);
        setUserId(null);
      } else {
        console.error('Failed to fetch current user.');
        setIsAuthenticated(false);
        setUser(null);
        setUserId(null);
      }
    } catch (error) {
      console.error('Error refreshing current user:', error);
    }
  }, []);
  

  return (
    <UserContext.Provider value={{ isAuthenticated, user, userId, login, logout, refreshUser }}>
      {children}
    </UserContext.Provider>
  );
};

export { UserContext, UserProvider };