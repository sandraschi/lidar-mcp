import { Component, type ReactNode } from "react";

export default class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div
        data-testid="page-error"
        className="rounded border border-red-800 bg-red-950 p-4 text-sm text-red-200"
      >
        <div className="mb-1 font-semibold">This page crashed.</div>
        <div className="text-red-300">{error.message}</div>
        <button
          onClick={() => this.setState({ error: null })}
          className="mt-3 rounded bg-red-900 px-3 py-1 hover:bg-red-800"
        >
          Retry
        </button>
      </div>
    );
  }
}
