import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { classification } from '../services/classification';
import '../styles/PredictPage.css';

const PredictPage = () => {
  const [productName, setProductName] = useState('');
  const [marketplace, setMarketplace] = useState('wildberries');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');

  const handlePredict = async () => {
    if (!productName.trim()) {
      setError('Введите название товара');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults([]);
    
    try {
      const data = await classification.classificationProduct(productName, marketplace);
      setResults([{
        product_name: data.product_name,
        category: data.category || data.category_name,
        category_path: data.category_path,
        hierarchy: data.hierarchy,
        marketplace: data.marketplace,
        confidence: (data.confidence * 100).toFixed(2),
        top_3: data.top_3
      }]);
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка предсказания');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Пожалуйста, загрузите CSV файл');
      return;
    }

    setCsvFile(file);
    setLoading(true);
    setError('');
    setResults([]);

    try {
      const data = await classification.classificationFromFile(file, marketplace);
      setResults(data.results || []);
      setUploadProgress(100);
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при загрузке файла');
    } finally {
      setLoading(false);
    }
  };

  const downloadResults = () => {
    if (results.length === 0) return;

    const csv = [
      ['Товар', 'Категория', 'Путь категории', 'Уверенность (%)'].join(','),
      ...results.map(r => [
        `"${r.product_name}"`,
        `"${r.category || r.category_name || ''}"`,
        `"${r.category_path || ''}"`,
        r.confidence
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `classifications_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleLogout = () => {
    classification.logout();
    navigate('/login');
  };

  return (
    <div className="predict-page">
      <div className="header">
        <div className="container flex flex-between items-center">
          <div>
            <h1 className="header-title">Система классификации товаров</h1>
          </div>
          <div className="flex items-center gap-lg">
            {role === 'admin' && (
                <button 
                  className="btn btn-secondary btn-sm"
                  onClick={() => navigate('/admin/users')}
                >
                  👥 Пользователи
                </button>
              )}
            <div className="user-info">
              <span className="user-name">{username}</span>
              <span className="user-role">{role}</span>
            </div>
            <button 
              className="btn btn-outline btn-sm"
              onClick={handleLogout}
            >
              Выход
            </button>
          </div>
        </div>
      </div>

      <div className="container">
        <div className="predict-content">
          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          <div className="card">
            <div className="card-header">
              <h2>Классификация товара</h2>
            </div>
            
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Выберите маркетплейс</label>
                <select
                  className="form-input"
                  value={marketplace}
                  onChange={(e) => setMarketplace(e.target.value)}
                  disabled={loading}
                >
                  <option value="wildberries">Wildberries</option>
                  <option value="ozon">Ozon</option>
                  <option value="yandex_market">Яндекс Маркет</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Введите название товара</label>
                <div className="flex gap-md">
                  <input
                    type="text"
                    className="form-input"
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handlePredict()}
                    placeholder="Например: Смартфон Apple iPhone 14 Pro Max 256GB..."
                    disabled={loading}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handlePredict}
                    disabled={loading || !productName.trim()}
                  >                    Классифицировать
                  </button>
                </div>
              </div>

              <div className="divider">или</div>

              <div className="form-group">
                <label className="form-label">Загрузить CSV файл с товарами</label>
                <div className="flex gap-md">
                  <label className="file-input-label">
                    <input
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      disabled={loading}
                      className="hidden"
                    />
                    <span className="btn btn-secondary">
                      Выбрать файл
                    </span>
                  </label>
                  {csvFile && (
                    <span className="file-name">{csvFile.name}</span>
                  )}
                </div>
                <p className="form-hint">
                  Формат: CSV с колонкой "product_name"
                </p>
              </div>

              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              )}
            </div>
          </div>

          {results.length > 0 && (
            <div className="card">
              <div className="card-header flex flex-between items-center">
                <h2>📊 Результаты классификации ({results.length})</h2>
                <button
                  className="btn btn-success btn-sm"
                  onClick={downloadResults}
                >
                  Выгрузить CSV
                </button>
              </div>

              <div className="results-table">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Товар</th>
                      <th>Категория</th>
                      <th>Путь категории</th>
                      <th>Уверенность</th>
                      <th>Топ-3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((result, idx) => (
                      <tr key={idx}>
                        <td className="truncate">{result.product_name}</td>
                        <td>
                          <span className="badge badge-primary">
                            {result.category || result.category_name}
                          </span>
                        </td>
                        <td className="text-secondary text-xs">
                          {result.category_path ? (
                            <div className="category-path">
                              {result.hierarchy?.map((level, i) => (
                                <span key={i}>
                                  {level}
                                  {i < result.hierarchy.length - 1 && ' / '}
                                </span>
                              )) || result.category_path}
                            </div>
                          ) : '-'}
                        </td>
                        <td>
                          <span className="confidence-score">
                            {result.confidence}%
                          </span>
                        </td>
                        <td className="text-secondary text-xs">
                          {result.top_3?.map((cat, i) => (
                            <div key={i}>
                              {cat.category} ({(cat.confidence * 100).toFixed(0)}%)
                            </div>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Пустое состояние */}
          {results.length === 0 && !loading && (
            <div className="empty-state">
              <p>Выполните классификацию товара или загрузите CSV файл</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PredictPage;