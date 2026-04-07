/**
 * Confidence Slider Component
 * 
 * A slider for adjusting the confidence threshold (0.0 - 1.0).
 * 
 * Requirements:
 * - 6.1: THE Frontend SHALL 提供置信度阈值滑块组件，范围 0.0-1.0
 * - 6.4: THE 滑块组件 SHALL 显示当前阈值数值
 */

import React from 'react';
import './ConfidenceSlider.css';

interface ConfidenceSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

/**
 * 置信度阈值滑块组件
 * 
 * 验证: 需求 6.1, 6.4
 */
export const ConfidenceSlider: React.FC<ConfidenceSliderProps> = ({ 
  value, 
  onChange,
  disabled = false 
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    // Clamp to valid range [0, 1]
    const clampedValue = Math.max(0, Math.min(1, newValue));
    onChange(clampedValue);
  };
  
  // Format value as percentage for display
  const percentage = Math.round(value * 100);
  
  return (
    <div className={`confidence-slider ${disabled ? 'confidence-slider--disabled' : ''}`}>
      <label className="confidence-slider__label">
        Confidence Threshold
        <span className="confidence-slider__value">{percentage}%</span>
      </label>
      <div className="confidence-slider__track-container">
        <input 
          type="range" 
          className="confidence-slider__input"
          min="0" 
          max="1" 
          step="0.05" 
          value={value} 
          onChange={handleChange}
          disabled={disabled}
          aria-label="Confidence threshold"
        />
        <div 
          className="confidence-slider__fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="confidence-slider__labels">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
    </div>
  );
};

export default ConfidenceSlider;
