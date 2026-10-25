import React from 'react';
import '../styles/components/Slider.css';

const Slider = ({
  min = 0,
  max = 100,
  value = 50,
  onChange,
  label,
  unit = '',
  step = 1,
  disabled = false,
  id,
}) => {
  return (
    <div className="slider-wrapper">
      {label && (
        <div className="slider-header">
          <label htmlFor={id}>{label}</label>
          <span className="slider-value">
            {value}
            {unit}
          </span>
        </div>
      )}
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        step={step}
        disabled={disabled}
        className="slider-input"
      />
      <div className="slider-range">
        <span className="range-min">{min}</span>
        <span className="range-max">
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
};

export default Slider;
