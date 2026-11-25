/**
 * Reference-counted page scroll lock for modal surfaces. The document keeps
 * `scrollbar-gutter: stable` (base.css), so locking never shifts the layout sideways.
 */
let locks = 0;

export function lockPageScroll(): () => void {
  const root = document.documentElement;
  if (locks === 0) root.dataset.scrollLocked = "true";
  locks += 1;
  let released = false;
  return () => {
    if (released) return;
    released = true;
    locks -= 1;
    if (locks === 0) delete root.dataset.scrollLocked;
  };
}
