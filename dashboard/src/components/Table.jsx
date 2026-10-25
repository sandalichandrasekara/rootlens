import React from 'react';
import '../styles/components/Table.css';

const Table = ({ columns, data, striped = true, hoverable = true, className = '' }) => {
  return (
    <div className={`table-wrapper ${className}`}>
      <table className={`table ${striped ? 'striped' : ''} ${hoverable ? 'hoverable' : ''}`}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={{ width: col.width }}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length > 0 ? (
            data.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td key={col.key}>
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length} className="empty-state">
                No data available
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default Table;
