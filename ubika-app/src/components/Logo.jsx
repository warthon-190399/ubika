/** Logo e isotipo oficiales (public/brand/). */
export function Mark({ size = 30 }) {
  return <img src="/brand/ubika-isotipo.svg" alt="" width={size} height={size} aria-hidden="true" />;
}

export default function Logo() {
  return (
    <span className="logo">
      <img src="/brand/ubika-logo.svg" alt="ubika" />
    </span>
  );
}
