import React from 'react';

interface State {
  hasError: boolean;
  error: string | null;
}

interface Props {
  children: React.ReactNode;
  fallbackMessage?: string;
  onReset?: () => void;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[LM-Screen ErrorBoundary] Caught render error:', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          margin: '24px',
          padding: '20px 24px',
          background: 'rgba(233, 137, 126, 0.08)',
          border: '1px solid #e8897e',
          borderRadius: '12px',
          color: 'var(--text-primary, #1a1a2e)',
        }}>
          <p style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '8px', color: '#c0392b' }}>
            ⚠ {this.props.fallbackMessage || 'Something went wrong while displaying the screening result.'}
          </p>
          {this.state.error && (
            <p style={{ fontSize: '0.8rem', color: '#666', marginBottom: '12px', fontFamily: 'monospace' }}>
              {this.state.error}
            </p>
          )}
          <button
            type="button"
            onClick={this.handleReset}
            style={{
              padding: '8px 18px',
              background: 'var(--color-primary, #2a9d8f)',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.88rem',
              cursor: 'pointer',
            }}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
