import React from 'react';
import '../styles/components/ToggleSwitch.css';

const ToggleSwitch = ({ checked = false, onChange, label, disabled = false, id }) => {
  return (
    <div className="toggle-wrapper">
      {label && <label htmlFor={id}>{label}</label>}
      <button
        id={id}
        className={`toggle-switch ${checked ? 'on' : 'off'}`}
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
        role="switch"
        aria-checked={checked}
      >
        <span className="toggle-slider"></span>
      </button>
    </div>
  );
};

export default ToggleSwitch;
