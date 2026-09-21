import * as React from "react"
import { cn } from "./Button" // Reuse utility

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full px-3 py-2",
          "bg-white text-text text-sm",
          "border border-border-medium rounded-md",
          "placeholder:text-text-placeholder",
          "focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent",
          "transition-all duration-150",
          "disabled:bg-background-tertiary disabled:cursor-not-allowed",
          "neumorphic-inset", // Add advanced effect
          {
            'border-accent-red focus:ring-accent-red': error,
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
