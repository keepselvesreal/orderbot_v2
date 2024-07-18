import React from 'react';
import Login from './Login';

const Navbar = ({ isAuthenticated, onLogout, onSignIn }) => {
  const handleLogout = (e) => {
    e.preventDefault();
    onLogout(); // 전달된 onLogout 함수 호출
  };

  const handleSignIn = (e) => {
    e.preventDefault();
    onSignIn(); // 전달된 onSignIn 함수 호출하여 로그인 페이지 표시 여부 토글
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-custom">
      <div className="container-fluid">
        <a className="navbar-brand" href="#">로고</a>
        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className="collapse navbar-collapse" id="navbarNav">
          <div className="navbar-nav">
            <a className="nav-link active" aria-current="page" href="#">주문</a>
            <a className="nav-link" href="#">상품 후기</a>
            <a className="nav-link" href="#">광장</a>
          </div>
          <ul className="navbar-nav ms-auto">
            {isAuthenticated ? (
              <li className="nav-item">
                <a className="nav-link" href="#logout" onClick={handleLogout}>로그아웃</a>
              </li>
            ) : (
              <li className="nav-item">
                <a className="nav-link" href="#login" onClick={handleSignIn}>로그인</a>
              </li>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

