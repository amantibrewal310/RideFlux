interface Props {
  size?: number;
}

export default function LoadingSpinner({ size = 32 }: Props) {
  return (
    <div
      className="loading-spinner"
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
