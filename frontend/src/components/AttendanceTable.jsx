import React, { useState, useEffect } from 'react';
import { getAttendanceReport, exportAttendance } from '../services/api';
import { format, subDays } from 'date-fns';
import { Download } from 'lucide-react';

export default function AttendanceTable() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [currentPage, setCurrentPage] = useState(1);
  const logsPerPage = 50;

  useEffect(() => {
    fetchRecords();
  }, [startDate, endDate]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const res = await getAttendanceReport(startDate, endDate);
      const sortedData = res.data.sort((a, b) => {
        const timeA = a.check_in ? new Date(a.check_in).getTime() : new Date(a.date).getTime();
        const timeB = b.check_in ? new Date(b.check_in).getTime() : new Date(b.date).getTime();
        return timeB - timeA;
      });
      setRecords(sortedData);
      setCurrentPage(1);
    } catch (error) {
      console.error("Error fetching attendance records", error);
    }
    setLoading(false);
  };

  const indexOfLastLog = currentPage * logsPerPage;
  const indexOfFirstLog = indexOfLastLog - logsPerPage;
  const currentLogs = records.slice(indexOfFirstLog, indexOfLastLog);
  const totalPages = Math.ceil(records.length / logsPerPage);

  const handleExport = async () => {
    try {
      const res = await exportAttendance(startDate, endDate);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Attendance_${startDate}_${endDate}.xlsx`);
      document.body.appendChild(link);
      link.click();
    } catch (error) {
      console.error("Error exporting data", error);
    }
  };


  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Attendance Logs</h2>
          <p className="page-subtitle">View and filter historical attendance data</p>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Start Date</label>
            <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>End Date</label>
            <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>

          <button className="btn btn-primary" onClick={handleExport}>
            <Download size={18} /> Export
          </button>
        </div>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Employee Name</th>
                <th>Check In</th>
                <th>Check Out</th>
                <th>Working Hours</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {currentLogs.map(record => {
                const checkInDate = record.check_in ? new Date(record.check_in) : null;
                const checkOutDate = record.check_out ? new Date(record.check_out) : null;
                
                const isLate = checkInDate && (checkInDate.getHours() > 10 || (checkInDate.getHours() === 10 && checkInDate.getMinutes() > 15));
                const isEarly = checkOutDate && (checkOutDate.getHours() < 17);

                return (
                  <tr key={record.id}>
                    <td>{record.date}</td>
                    <td>{record.employee?.full_name || 'Unknown'}</td>
                    <td>
                      {checkInDate ? format(checkInDate, 'HH:mm:ss') : '-'}
                      {isLate && <span className="badge" style={{background: '#fee2e2', color: '#b91c1c', marginLeft: '8px'}}>Late</span>}
                    </td>
                    <td>
                      {checkOutDate ? format(checkOutDate, 'HH:mm:ss') : '-'}
                      {isEarly && <span className="badge" style={{background: '#fef3c7', color: '#b45309', marginLeft: '8px'}}>Early Leave</span>}
                    </td>
                    <td>{record.working_hours ? record.working_hours.toFixed(2) : '0.00'}</td>
                    <td>
                      <span className={`badge badge-${record.status.toLowerCase()}`}>
                        {record.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {records.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center' }}>No records found for this date range</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {!loading && totalPages > 1 && (
        <div className="pagination-controls" style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '20px' }}>
          <button 
            disabled={currentPage === 1} 
            onClick={() => setCurrentPage(p => p - 1)}
            className="btn btn-secondary"
          >
            Prev
          </button>
          
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
            <button 
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`btn ${currentPage === page ? 'btn-primary' : 'btn-secondary'}`}
            >
              {page}
            </button>
          ))}

          <button 
            disabled={currentPage === totalPages} 
            onClick={() => setCurrentPage(p => p + 1)}
            className="btn btn-secondary"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
