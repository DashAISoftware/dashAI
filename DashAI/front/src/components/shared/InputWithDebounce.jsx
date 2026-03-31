import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import { Input } from "../configurableObject/Inputs/InputStyles";
import useDebounce from "../../hooks/useDebounce";
import { width } from "@mui/system";

/**
 * This is a HOC for an input with a debounce, it will update the value after a delay,
 * useful when you want to wait for the user to stop typing before updating the value
 * @param {function} onChange - The function to update the value
 * @param {number} delay - The delay to wait before updating the value
 * @param {any} value - The value to update
 */

export default function InputWithDebounce({
  onChange,
  delay = 300,
  value,
  ...rest
}) {
  const { onFocus: onFocusProp, onBlur: onBlurProp, ...restProps } = rest;
  const [inputValue, setInputValue] = useState(value ?? "");
  const [isEditing, setIsEditing] = useState(false);
  const debouncedValue = useDebounce(inputValue, delay);

  const handleChange = (event) => {
    setInputValue(event.target.value);
  };

  const handleFocus = (event) => {
    setInputValue(value ?? "");
    setIsEditing(true);
    onFocusProp?.(event);
  };

  const handleBlur = (event) => {
    setIsEditing(false);
    onBlurProp?.(event);
  };

  useEffect(() => {
    if (debouncedValue !== value) {
      onChange(debouncedValue);
    }
  }, [debouncedValue, onChange, value]);

  const displayValue = isEditing ? inputValue : value ?? inputValue ?? "";

  return (
    <Input
      value={displayValue}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      {...restProps}
    />
  );
}

InputWithDebounce.propTypes = {
  value: PropTypes.any,
  delay: PropTypes.number,
  onChange: PropTypes.func.isRequired,
};
