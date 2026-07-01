import axios from 'axios';

const instance = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
});

export const client = {
  instance,
};

