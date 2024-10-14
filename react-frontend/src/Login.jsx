import React, { useState, useContext } from 'react';
import axios from 'axios';
import { UserContext } from './UserContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const { login, refreshUser } = useContext(UserContext);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      await refreshUser(); // 로그인 후 사용자 정보 갱신

      navigate('/'); // 로그인 후 리다이렉트할 경로
    } catch (error) {
      console.error('Login error:', error);
      setError('Invalid username or password');
    }
  };

  const handleSignUpClick = () => {
    console.log("signup 클릭")
    navigate("/signup");
  };

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <h1 className="text-center">Login</h1>
          <form onSubmit={handleSubmit}>
            {error && <p className="text-danger">{error}</p>}
            <div className="mb-3">
              <label htmlFor="username" className="form-label">Username</label>
              <input 
                type="text" 
                className="form-control" 
                id="username" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
              />
            </div>
            <div className="mb-3">
              <label htmlFor="password" className="form-label">Password</label>
              <input 
                type="password" 
                className="form-control" 
                id="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
              />
            </div>
            <button type="submit" className="btn btn-primary w-100">Log In</button>
            <button type="button" className="btn btn-link w-100 mt-2" onClick={handleSignUpClick}>
              Sign Up
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;