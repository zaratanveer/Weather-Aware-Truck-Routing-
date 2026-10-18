import { useEffect, useState } from 'react';

/** `value`, but only after it has stopped changing for `delayMs`. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer); // a new keystroke restarts the wait
  }, [value, delayMs]);

  return debounced;
}
