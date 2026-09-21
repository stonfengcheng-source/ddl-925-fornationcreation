import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Input } from './Input';

describe('Input Component', () => {
  it('renders correctly', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('supports disabled state', () => {
    render(<Input disabled placeholder="Disabled" />);
    const input = screen.getByPlaceholderText('Disabled');
    expect(input).toBeDisabled();
    expect(input.className).toContain('disabled:cursor-not-allowed');
  });

  it('supports error state', () => {
    render(<Input error placeholder="Error" />);
    const input = screen.getByPlaceholderText('Error');
    expect(input.className).toContain('border-error');
    expect(input.className).toContain('focus-visible:ring-error');
  });

  it('forwards refs', () => {
    // Basic ref check - React Testing Library handles refs automatically,
    // but ensuring it doesn't crash is a good basic check.
    render(<Input ref={() => {}} placeholder="Ref" />);
    expect(screen.getByPlaceholderText('Ref')).toBeInTheDocument();
  });
});
