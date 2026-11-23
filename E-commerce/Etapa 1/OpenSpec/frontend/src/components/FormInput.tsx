import React from 'react';

interface FormInputProps {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string | null;
  placeholder?: string;
  required?: boolean;
}

export const FormInput: React.FC<FormInputProps> = ({
  id,
  label,
  type = 'text',
  value,
  onChange,
  error,
  placeholder,
  required = false,
}) => {
  return (
    <div className="mb-4">
      <label
        htmlFor={id}
        className="block text-sm font-semibold text-gray-700 mb-1"
      >
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors ${
          error ? 'border-red-500 bg-red-50' : 'border-gray-300'
        }`}
      />
      {error && (
        <p
          id={`${id}-error`}
          className="mt-1 text-sm text-red-600 font-medium"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
};
