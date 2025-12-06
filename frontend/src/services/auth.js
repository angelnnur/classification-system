import api from './api';

export const auth = {
    login: async (username, password) => {
        try {
            const response = await api.post('/auth/login', { username, password });
            localStorage.setItem('token', response.data.token);
            localStorage.setItem('username', JSON.stringify(response.data.user.username));
            localStorage.setItem('role', response.data.user.role)
            
            return response.data;
        } catch(error) {
            throw new Error('Ошибка входа в систему: ' + error)
        }
    },
    register: async (username, password, role = 'user')=> {
        try {
            const response = await api.post('/auth/register', { username, password, role });
            
            return response.data;
        } catch(error) {
            throw new Error('Ошибка создания пользователя: ' + error)
        }
        
    },
    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
    },
    getToken: () => {
        return localStorage.getItem('token');
    },
    getCurrentUser: () => {
        return localStorage.getItem('username');
    }
}