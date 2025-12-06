import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import PredictPage from './pages/PredictPage';
import AdminUsersPage from './pages/AdminUsersPage';
import './styles/index.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route 
          path="/predict" 
          element={
            <CheckToken>
              <PredictPage />
            </CheckToken>
          } 
        />
        
        <Route 
          path="/admin/users" 
          element={
            <CheckToken>
              <AdminUsersPage />
            </CheckToken>
          } 
        />
        
        <Route path="/" element={<Navigate to="/predict" />} />
        <Route path="*" element={<Navigate to="/predict" />} />
      </Routes>
    </BrowserRouter>
  );
}

function CheckToken({ children }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}