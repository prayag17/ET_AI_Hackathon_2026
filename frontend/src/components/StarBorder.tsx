import React from 'react'
import { cn } from '@/lib/utils'

type StarBorderProps<T extends React.ElementType> =
  React.ComponentPropsWithoutRef<T> & {
    as?: T
    className?: string
    children?: React.ReactNode
    color?: string
    speed?: React.CSSProperties['animationDuration']
    thickness?: number
  }

const StarBorder = <T extends React.ElementType = 'button'>({
  as,
  className,
  color = 'white',
  speed = '6s',
  thickness = 2,
  children,
  ...rest
}: StarBorderProps<T>) => {
  const Component = as || 'button'

  return (
    <Component
      className={cn(
        'relative inline-flex items-center justify-center overflow-hidden rounded-full',
        className,
      )}
      {...rest}
      style={{
        padding: `${thickness}px`,
        ...rest.style,
      }}
    >
      <div
        className="animate-star-movement-bottom absolute bottom-[-11px] right-[-250%] z-0 h-[50%] w-[300%] rounded-full opacity-70"
        style={{
          background: `radial-gradient(circle, ${color}, transparent 10%)`,
          animationDuration: speed,
        }}
      />
      <div
        className="animate-star-movement-top absolute left-[-250%] top-[-10px] z-0 h-[50%] w-[300%] rounded-full opacity-70"
        style={{
          background: `radial-gradient(circle, ${color}, transparent 10%)`,
          animationDuration: speed,
        }}
      />
      <div className="relative z-1 flex size-full items-center justify-center overflow-hidden rounded-full">
        {children}
      </div>
    </Component>
  )
}

export default StarBorder
