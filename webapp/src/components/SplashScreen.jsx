import { useRef, useEffect } from 'react'
import { animate, createScope } from 'animejs'
import { RootCentered } from '../styled'

export default function SplashScreen({ onDone }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope

    animate('.splash-logo', {
      opacity: [0, 1],
      scale: [0.8, 1],
      translateY: [20, 0],
      duration: 900,
      ease: 'out(3)',
    })

    const t = setTimeout(() => exit(), 2200)
    return () => {
      clearTimeout(t)
      scope.revert()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function exit() {
    setTimeout(() => onDone?.(), 700)
    try {
      const anim = animate('.splash-root', {
        opacity: [1, 0],
        duration: 500,
        ease: 'in(2)',
      })
      if (anim && typeof anim.then === 'function') {
        anim.then(() => onDone?.()).catch(() => {})
      }
    } catch (e) {
    }
  }

  return (
    <RootCentered ref={rootRef} className="splash-root">
      <img
        src="/fulllogo.svg"
        alt="MedVision"
        className="splash-logo"
        style={{ height: 550, width: 'auto', objectFit: 'contain' }}
      />
    </RootCentered>
  )
}
