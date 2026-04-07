/**
 * Rating Stars Component
 * 
 * A 1-5 star rating component for rating chunks and answers.
 * 
 * Requirements:
 * - 4.1: THE Frontend SHALL 在每个召回内容项旁显示评分组件
 * - 4.4: THE 评分组件 SHALL 支持 1-5 星评分
 * - 5.1: THE Frontend SHALL 在回答下方显示评分组件
 */

import React, { useState } from 'react';
import './RatingStars.css';

interface RatingStarsProps {
  value?: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
}

/**
 * 星级评分组件
 * 
 * 验证: 需求 4.1, 4.4, 5.1
 */
export const RatingStars: React.FC<RatingStarsProps> = ({ 
  value, 
  onChange, 
  disabled = false,
  size = 'medium' 
}) => {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  
  const displayValue = hoverValue !== null ? hoverValue : (value || 0);
  
  const handleClick = (rating: number) => {
    if (!disabled) {
      onChange(rating);
    }
  };
  
  const handleMouseEnter = (rating: number) => {
    if (!disabled) {
      setHoverValue(rating);
    }
  };
  
  const handleMouseLeave = () => {
    setHoverValue(null);
  };
  
  const sizeClass = `rating-stars--${size}`;
  
  return (
    <div 
      className={`rating-stars ${sizeClass} ${disabled ? 'rating-stars--disabled' : ''}`}
      onMouseLeave={handleMouseLeave}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={`rating-star ${star <= displayValue ? 'rating-star--filled' : ''}`}
          onClick={() => handleClick(star)}
          onMouseEnter={() => handleMouseEnter(star)}
          disabled={disabled}
          aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
        >
          ★
        </button>
      ))}
      {value && <span className="rating-value">({value}/5)</span>}
    </div>
  );
};

export default RatingStars;
