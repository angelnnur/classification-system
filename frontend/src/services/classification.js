import api from './api';

export const classification = {
    classificationProduct:  async (productName) => {
        const response = await api.post('/predict_category', {
            product_name: productName
        });
        return response.data;
    },
    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
    },
    classificationFromFile: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post('/predict_category_from_file', formData, {headers: { 'Content-Type': 'multipart/form-data' }});
        return response.data;
    }
}