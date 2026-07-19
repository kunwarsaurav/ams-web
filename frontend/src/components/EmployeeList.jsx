import React, { useState, useEffect } from 'react';
import { getEmployees, createEmployee, updateEmployee, deleteEmployee } from '../services/api';
import { Edit2, Trash2, Plus } from 'lucide-react';
import { wsManager } from '../services/websocket';

export default function EmployeeList() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState(null);
  
  const [formData, setFormData] = useState({
    machine_user_id: '',
    full_name: '',
    department: '',
    designation: '',
    status: 'Active'
  });

  useEffect(() => {
    fetchEmployees();

    const unsubNew = wsManager.subscribe('NEW_EMPLOYEE', () => {
      fetchEmployees();
    });

    const unsubUpdate = wsManager.subscribe('EMPLOYEE_UPDATED', () => {
      fetchEmployees();
    });

    return () => {
      unsubNew();
      unsubUpdate();
    };
  }, []);

  const fetchEmployees = async () => {
    setLoading(true);
    try {
      const res = await getEmployees();
      setEmployees(res.data);
    } catch (error) {
      console.error("Error fetching employees", error);
    }
    setLoading(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const openAddModal = () => {
    setEditingId(null);
    setFormData({
      machine_user_id: '',
      full_name: '',
      department: '',
      designation: '',
      status: 'Active'
    });
    setShowModal(true);
  };

  const openEditModal = (emp) => {
    setEditingId(emp.id);
    setFormData({
      machine_user_id: emp.machine_user_id,
      full_name: emp.full_name,
      department: emp.department,
      designation: emp.designation,
      status: emp.status
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this employee? This will also remove them from the machine.")) return;
    
    try {
      await deleteEmployee(id);
      await fetchEmployees();
    } catch (error) {
      console.error("Error deleting employee", error);
      alert("Failed to delete employee");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingId) {
        await updateEmployee(editingId, formData);
      } else {
        await createEmployee(formData);
      }
      await fetchEmployees();
      setShowModal(false);
    } catch (error) {
      console.error("Error saving employee", error);
      alert(error.response?.data?.detail || "Failed to save employee");
    }
    setSubmitting(false);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Employees</h2>
          <p className="page-subtitle">Manage your organization's workforce</p>
        </div>
        <button className="btn btn-primary" onClick={openAddModal}>
          <Plus size={18} /> Add Employee
        </button>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Machine ID</th>
                <th>Name</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {employees.map(emp => (
                <tr key={emp.id}>
                  <td>{emp.machine_user_id}</td>
                  <td>{emp.full_name}</td>
                  <td>{emp.department}</td>
                  <td>{emp.designation}</td>
                  <td>
                    <span className={`badge badge-${emp.status.toLowerCase()}`}>
                      {emp.status}
                    </span>
                    {emp.is_synced === 0 && (
                      <span className="badge" style={{ marginLeft: '8px', background: 'var(--warning)', color: '#fff', fontSize: '10px' }}>
                        Pending Sync
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn-icon" onClick={() => openEditModal(emp)} title="Edit" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--primary)', marginRight: '12px' }}>
                      <Edit2 size={18} />
                    </button>
                    <button className="btn-icon" onClick={() => handleDelete(emp.id)} title="Delete" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--danger)' }}>
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {employees.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center' }}>No employees found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>{editingId ? 'Edit Employee' : 'Add New Employee'}</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
                This will save the employee to the database and sync them to the attendance machine.
              </p>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Full Name</label>
                <input required type="text" name="full_name" className="form-control" value={formData.full_name} onChange={handleInputChange} />
              </div>
              <div className="form-group">
                <label>Machine User ID (Must be unique)</label>
                <input required type="text" name="machine_user_id" className="form-control" value={formData.machine_user_id} onChange={handleInputChange} disabled={!!editingId} title={editingId ? "Machine ID cannot be changed" : ""} />
              </div>
              <div className="form-group">
                <label>Department</label>
                <input required type="text" name="department" className="form-control" value={formData.department} onChange={handleInputChange} />
              </div>
              <div className="form-group">
                <label>Designation</label>
                <input required type="text" name="designation" className="form-control" value={formData.designation} onChange={handleInputChange} />
              </div>
              {editingId && (
                <div className="form-group">
                  <label>Status</label>
                  <select name="status" className="form-control" value={formData.status} onChange={handleInputChange}>
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              )}
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)} disabled={submitting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Saving & Syncing...' : 'Save Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
