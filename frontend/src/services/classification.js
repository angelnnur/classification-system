import api from './api';

export const classification = {
    classificationProduct:  async (productName, marketplace = 'wildberries') => {
        const response = await api.post('/predict_category', {
            product_name: productName,
            marketplace: marketplace
        });
        return response.data;
    },
    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
    },
    classificationFromFile: async (file, marketplace = 'wildberries') => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('marketplace', marketplace);

        const response = await api.post('/predict_category_from_file', formData, {headers: { 'Content-Type': 'multipart/form-data' }});
        return response.data;
    }
}