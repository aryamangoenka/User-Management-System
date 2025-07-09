import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// Types
export interface User {
  user_id: number;
  user_name: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  phone_number: string;
  address: string;
  role: 'admin' | 'manager' | 'user' | 'staff';
  is_active: boolean;
  last_login: string | null;
  create_at: string;
  created_at: string;
  date_joined: string;
  profile_picture?: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  address: string;
  role: string;
  password: string;
  password_confirm: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  message: string;
}

export interface UsersResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: User[];
}

// API Functions
export const authAPI = {
  register: (data: RegisterRequest): Promise<AuthResponse> =>
    api.post('/auth/register/', data).then(res => res.data),
  
  login: (data: LoginRequest): Promise<AuthResponse> =>
    api.post('/auth/login/', data).then(res => res.data),
  
  logout: (): Promise<{ message: string }> =>
    api.post('/auth/logout/').then(res => res.data),
};

export const userAPI = {
  getProfile: (): Promise<User> =>
    api.get('/profile/').then(res => res.data),
  
  updateProfile: (data: Partial<User>): Promise<{ user: User; message: string }> =>
    api.put('/profile/update/', data).then(res => res.data),
  
  uploadProfilePicture: (file: File): Promise<{ user: User; message: string }> => {
    const formData = new FormData();
    formData.append('profile_picture', file);
    return api.put('/profile/update/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },
  
  getUsers: (): Promise<UsersResponse> =>
    api.get('/users/').then(res => res.data),
  
  getUser: (id: number): Promise<User> =>
    api.get(`/users/${id}/`).then(res => res.data),
  
  createUser: (data: RegisterRequest): Promise<User> =>
    api.post('/users/', data).then(res => res.data),
  
  updateUser: (id: number, data: Partial<User>): Promise<User> =>
    api.put(`/users/${id}/`, data).then(res => res.data),
  
  deleteUser: (id: number): Promise<void> =>
    api.delete(`/users/${id}/`).then(res => res.data),
};

export const apiRoot = (): Promise<any> =>
  api.get('/').then(res => res.data);

export default api; 