# 🚀 Инструкция по развёртыванию (Frontend + Backend)

Этот проект состоит из двух независимых частей:
- **Backend** (Flask) на Render
- **Frontend** (Vue.js) на Netlify

---

## 📦 Backend (Render)

**Текущее состояние:** ✅ Развёрнут
**URL:** https://classification-system-2.onrender.com

### Как это работает:

1. Код из `backend/` папки автоматически деплоится на Render
2. Render собирает Docker образ из `Dockerfile`
3. Flask приложение запускается на порту 5000

### Переменные окружения на Render:

Нужно установить в Render Dashboard → Settings → Environment:

```
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
FRONTEND_URL=https://your-netlify-domain.netlify.app
```

### API Endpoints:

- Health check: `GET https://classification-system-2.onrender.com/health`
- API routes: `GET/POST https://classification-system-2.onrender.com/api/*`

---

## 🎨 Frontend (Netlify)

**Текущее состояние:** ❌ Еще не развёрнут (см. инструкцию ниже)

### Как это работает:

1. Netlify слушает изменения в репо
2. При каждом push → автоматический build и deploy
3. Vue.js приложение собирается в статические файлы (`dist/`)
4. Файлы раздаются по HTTPS через CDN

### Пошаговая инструкция по развёртыванию на Netlify:

#### **Шаг 1: Подготовить локально**

```bash
cd frontend
npm run build
cd ..
git add frontend/dist/ frontend/.env frontend/.env.production
git commit -m "Add frontend build and env files"
git push
```

#### **Шаг 2: Залогиниться на Netlify**

1. Перейди на https://netlify.com
2. Нажми "Sign up" или "Log in"
3. Выбери вариант через GitHub (удобнее всего)

#### **Шаг 3: Создать новый site**

1. В Netlify Dashboard нажми **"Add new site"**
2. Выбери **"Import an existing project"**
3. Выбери GitHub provider
4. Выбери репо `classification-system`

#### **Шаг 4: Настроить Build settings**

При импорте заполни:

| Поле | Значение |
|------|----------|
| **Base directory** | `frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `dist` |

#### **Шаг 5: Нажми "Deploy"**

Nelify начнёт:
1. Клонировать репо
2. Установит зависимости (`npm install`)
3. Запустит сборку (`npm run build`)
4. Раздаст содержимое `frontend/dist/`

#### **Шаг 6: Получишь ссылку**

Тип: `https://your-site-name.netlify.app`

Ошибка? Проверь логи в Netlify Dashboard → **Deploys** → клик на последний деплой → **Deploy log**

---

## 🔗 Как они общаются (CORS)

**Проблема:** Frontend на `netlify.app`, Backend на `onrender.com` → разные домены

**Решение:** CORS (Cross-Origin Resource Sharing) в `backend/src/api/app.py`

```python
allowed_origins = [
    "http://localhost:5173",  # local dev
    "https://your-netlify-domain.netlify.app",  # production
]
CORS(app, origins=allowed_origins, ...)
```

### Frontend делает запрос:

```javascript
// frontend/src/services/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

fetch(`${API_URL}/api/products`, {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
  }
})
```

**Локально** (`npm run dev`):
- Frontend слушает `http://localhost:5173`
- Backend слушает `http://localhost:5000`
- `.env` указывает `VITE_API_URL=http://localhost:5000`

**В Production**:
- Frontend раздаётся с Netlify CDN
- `.env.production` указывает `VITE_API_URL=https://classification-system-2.onrender.com`
- CORS разрешает запросы с `netlify.app` домена

---

## ✅ Checklist

### Backend (Render):
- [x] Dockerfile создан в корне репо
- [x] requirements.txt в backend/
- [x] CORS настроен
- [x] Развёрнут на Render

### Frontend (Netlify):
- [ ] Собран локально (`npm run build`)
- [ ] Залит в репо (`frontend/dist/`)
- [ ] Создан Netlify site
- [ ] Build settings настроены
- [ ] Получена ссылка

### Финальная проверка:
- [ ] Фронтенд открывается: `https://your-site.netlify.app/`
- [ ] Backend здоров: `https://classification-system-2.onrender.com/health`
- [ ] Фронтенд может делать запросы к backend
- [ ] Нет CORS ошибок в консоли браузера

---

## 🐛 Troubleshooting

### Frontend показывает пустую страницу

**Причина:** Ошибка при загрузке или сборке

**Что делать:**
1. Открой DevTools (F12)
2. Посмотри консоль на ошибки
3. Посмотри Network tab на failed requests
4. Проверь Netlify Deploy log

### CORS ошибка в консоли

```
Access to XMLHttpRequest at 'https://...' from origin 'https://your-site.netlify.app'
has been blocked by CORS policy
```

**Решение:**
1. Проверь, что твой Netlify URL добавлен в `allowed_origins` в `backend/src/api/app.py`
2. Redeploy backend на Render
3. Обнови страницу в браузере (Ctrl+F5)

### Backend не отвечает (502 ошибка)

**Проверь на Render:**
1. Нажми на Web Service
2. Посмотри **Logs**
3. Ищи ошибки запуска приложения

### Фронтенд деплой падает

**Посмотри Netlify логи:**
1. Netlify Dashboard → Deploys → последний
2. Deploy log → ищи ошибку
3. Обычно: `npm install` или `npm run build` ошибка

---

## 📝 Отправить препу

Когда всё готово, отправь ссылки:

```
🎨 Frontend: https://your-site.netlify.app/
⚙️  Backend: https://classification-system-2.onrender.com/
📦 GitHub: https://github.com/angelnnur/classification-system
```

Преп сможет:
- Открыть фронтенд и протестировать функционал
- Проверить API через `/api/` endpoints
- Посмотреть исходный код на GitHub

---

## 🚀 Автоматический CI/CD

Сейчас всё работает автоматически:

1. Ты пушишь в GitHub
2. Render автоматически перестраивает backend
3. Netlify автоматически перестраивает frontend
4. ✅ Новая версия live!

Не нужно ничего делать вручную. Just `git push` and it works! 🎉
