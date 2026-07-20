import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || `http://${window.location.hostname || '127.0.0.1'}:8080`;
const api = axios.create({
    baseURL: baseURL,
    withCredentials: true, // Send cookies automatically
    headers: {
        'Content-Type': 'application/json',
    },
});

// Auth
export const login = (username, password) => api.post('/auth/login', { username, password });
export const logout = () => api.post('/auth/logout');
export const verifySession = () => api.get('/auth/me');

// Employees
export const getEmployees = () => api.get('/employees');
export const createEmployee = (data) => api.post('/employees', data);
export const updateEmployee = (id, data) => api.put(`/employees/${id}`, data);
export const deleteEmployee = (id) => api.delete(`/employees/${id}`);

// Attendance
export const syncAttendance = () => api.post('/attendance/sync');
export const getTodayAttendance = () => api.get('/attendance/today');
export const getAttendanceReport = (startDate, endDate) => api.get(`/attendance/report`, { params: { start_date: startDate, end_date: endDate } });
export const getMonthlySummary = (year, month) => api.get(`/attendance/monthly`, { params: { year, month } });
export const getEmployeeAttendance = (empId) => api.get(`/attendance/employee/${empId}`);
export const exportAttendance = (startDate, endDate) => api.get(`/attendance/export`, { params: { start_date: startDate, end_date: endDate }, responseType: 'blob' });

export const getTodayRawLogs = () => api.get('/attendance/logs/today');
export const deleteTodayAttendance = () => api.delete('/attendance/today');
export const deleteAttendanceReport = (startDate, endDate) => api.delete('/attendance/report', { params: { start_date: startDate, end_date: endDate } });
export const pingDevice = () => api.get('/device/ping');
export const getDeviceSettings = () => api.get('/device/settings');
export const updateDeviceSettings = (data) => api.post('/device/settings', data);

// AI
export const getAIAlerts = (weeksAgo = 0) => api.get('/ai/alerts', { params: { weeks_ago: weeksAgo } });

export default api;
