import * as React from "react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  effect?: '3d' | 'glossy' | 'ripple' | 'none' // Added new effects prop
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', effect = 'none', ...props }, ref) => {
    
    // Auto-apply effects based on usage context if not specified
    const appliedEffect = effect !== 'none' ? effect : 
      (className?.includes('button-3d') ? '3d' : 'none');

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50 select-none",
          {
            // Variants
            'bg-accent text-white hover:bg-accent/90': variant === 'primary',
            'bg-white text-text border border-border hover:bg-background-secondary': variant === 'secondary',
            'hover:bg-background-secondary text-text': variant === 'ghost',
            'bg-accent-red text-white hover:bg-accent-red/90': variant === 'destructive',
            
            // Sizes
            'h-8 px-3 text-xs': size === 'sm',
            'h-9 px-4 py-2 text-sm': size === 'md',
            'h-11 px-8 text-base': size === 'lg',

            // Effects
            'button-3d': appliedEffect === '3d',
            'glossy': appliedEffect === 'glossy',
            'ripple overflow-hidden relative': appliedEffect === 'ripple' || variant === 'primary', // Apply ripple to primary by default
          },
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
