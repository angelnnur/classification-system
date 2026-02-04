import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../services/auth';
import api from '../services/api';
import '../styles/AdminUsersPage.css';

const AdminUsersPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    role: 'user'
  });
  const navigate = useNavigate();
  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');

  useEffect(() => {
    // Проверка доступа админа
    if (role !== 'admin') {
      navigate('/predict');
      return;
    }
    loadUsers();
  }, [role, navigate]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/users');
      setUsers(response.data.users || []);
      setError('');
    } catch (err) {
      setError('Ошибка загрузки пользователей');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewUserForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!newUserForm.username.trim()) {
      setError('❗ Username не может быть пустым');
      return false;
    }
    if (newUserForm.username.length < 3) {
      setError('❗ Username минимум 3 символа');
      return false;
    }
    if (!newUserForm.password) {
      setError('❗ Пароль не может быть пустым');
      return false;
    }
    if (newUserForm.password.length < 6) {
      setError('❗ Пароль минимум 6 символов');
      return false;
    }
    if (newUserForm.password !== newUserForm.confirmPassword) {
      setError('❗ Пароли не совпадают');
      return false;
    }
    return true;
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    try {
      setLoading(true);
      setError('');
      
      await auth.register(
        newUserForm.username,
        newUserForm.password,
        newUserForm.role
      );

      setSuccess(`✔️ Пользователь "${newUserForm.username}" успешно создан!`);
      setNewUserForm({ username: '', password: '', confirmPassword: '', role: 'user' });
      setShowModal(false);
      
      setTimeout(() => {
        setSuccess('');
        loadUsers();
      }, 2000);
    } catch (err) {
      const errorMsg = err.response?.data?.error || '❗ Ошибка при создании пользователя';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (!window.confirm(`Вы уверены, что хотите удалить пользователя "${userName}"?`)) {
      return;
    }

    try {
      await api.delete(`/users/${userId}`);
      setSuccess(`✔️ Пользователь "${userName}" удалён!`);
      setTimeout(() => {
        setSuccess('');
        loadUsers();
      }, 2000);
    } catch (err) {
      setError('❗ Ошибка при удалении пользователя');
    }
  };

  const handleLogout = () => {
    auth.logout();
    navigate('/login');
  };

  const getRoleColor = (userRole) => {
    return userRole === 'admin' ? 'badge-primary' : 'badge-success';
  };

  return (
    <div className="admin-page">
      {/* Хедер */}
      <div className="header">
        <div className="container flex flex-between items-center">
          <div>
            <h1 className="header-title">👥 Управление пользователями</h1>
          </div>
          <div className="flex items-center gap-lg">
            <div className="user-info">
              <span className="user-name">{username}</span>
              <span className="user-role admin">admin</span>
            </div>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => navigate('/predict')}
            >
              🔙 Назад
            </button>
            <button 
              className="btn btn-outline btn-sm"
              onClick={handleLogout}
            >
             ❌ Выход
            </button>
          </div>
        </div>
      </div>

      <div className="container">
        <div className="admin-content">
          {/* Сообщения */}
          {error && <div className="alert alert-error">⚠️ {error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          {/* Кнопка добавления */}
          <div className="admin-header">
            <button
              className="btn btn-primary"
              onClick={() => setShowModal(true)}
            >
              ➕ Добавить пользователя
            </button>
          </div>

          {/* Таблица пользователей */}
          {loading ? (
            <div className="loading-state">
              <span className="spinner"></span>
              <p>Загрузка пользователей...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">👤</div>
              <p>Нет пользователей</p>
            </div>
          ) : (
            <div className="card">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Роль</th>
                    <th>Дата создания</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(user => (
                    <tr key={user.id}>
                      <td>#{user.id}</td>
                      <td className="font-semibold">{user.username}</td>
                      <td>
                        <span className={`badge ${getRoleColor(user.role)}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="text-secondary text-xs">
                        {new Date(user.created_at).toLocaleDateString('ru-RU')}
                      </td>
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteUser(user.id, user.username)}
                        >
                          🗑️ Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Модальное окно создания пользователя */}
      {showModal && (
        <div className="modal active" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Создать нового пользователя</h2>
              <button
                className="modal-close"
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="modal-body">
              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  type="text"
                  name="username"
                  className="form-input"
                  value={newUserForm.username}
                  onChange={handleInputChange}
                  placeholder="Введите username"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Пароль</label>
                <input
                  type="password"
                  name="password"
                  className="form-input"
                  value={newUserForm.password}
                  onChange={handleInputChange}
                  placeholder="Минимум 6 символов"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Подтверждение пароля</label>
                <input
                  type="password"
                  name="confirmPassword"
                  className="form-input"
                  value={newUserForm.confirmPassword}
                  onChange={handleInputChange}
                  placeholder="Повторите пароль"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Роль</label>
                <select
                  name="role"
                  className="form-select"
                  value={newUserForm.role}
                  onChange={handleInputChange}
                  disabled={loading}
                >
                  <option value="user">Пользователь</option>
                  <option value="admin">Администратор</option>
                </select>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowModal(false)}
                  disabled={loading}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? <span className="spinner"></span> : '➕'}
                  Создать пользователя
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsersPage;