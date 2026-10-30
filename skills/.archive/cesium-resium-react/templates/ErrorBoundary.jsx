import React from 'react'

// React error boundaries MUST be class components. Wraps <Viewer> so a Cesium
// init crash shows a fallback instead of white-screening the app.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message ?? 'Unknown error' }
  }

  componentDidCatch(error, info) {
    console.error('[DigitalTwin] Viewer crashed:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="dt-fallback">
            <h2>3D canvas unavailable</h2>
            <p>The spatial viewer failed to initialize.</p>
            <code>{this.state.message}</code>
          </div>
        )
      )
    }
    return this.props.children
  }
}
