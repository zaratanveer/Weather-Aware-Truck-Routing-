import { useId, useState, type KeyboardEvent } from 'react';

import type { Place } from '../api/types';
import { usePlaceSearch } from '../hooks/usePlaceSearch';

interface PlaceInputProps {
  label: string;
  placeholder: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
  error?: string;
}

/** A text box with place suggestions (an accessible "combobox"). */
export function PlaceInput({ label, placeholder, value, onChange, error }: PlaceInputProps) {
  const id = useId();
  const listId = `${id}-suggestions`;
  const [text, setText] = useState(value?.label ?? '');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  // Only search while the user is typing, not after a place was picked.
  const { results, loading, error: searchError } = usePlaceSearch(text, open && value === null);
  const showList = open && value === null && (results.length > 0 || loading || searchError !== null);

  function choose(place: Place) {
    setText(place.label);
    onChange(place);
    setOpen(false);
    setActiveIndex(-1);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!showList || results.length === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      choose(results[activeIndex]);
    } else if (event.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div className="field place-input">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-expanded={showList}
        aria-controls={listId}
        aria-invalid={error ? true : undefined}
        aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        placeholder={placeholder}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
          setActiveIndex(-1);
          if (value) onChange(null); // editing the text un-picks the place
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={handleKeyDown}
      />
      {showList && (
        <ul id={listId} role="listbox" className="suggestions">
          {loading && results.length === 0 && <li className="suggestion-status">Searching…</li>}
          {searchError && <li className="suggestion-status error-text">{searchError}</li>}
          {results.map((place, index) => (
            <li
              key={`${place.label}-${place.lat}-${place.lon}`}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={index === activeIndex ? 'suggestion active' : 'suggestion'}
              // mousedown (not click) fires before the input's blur closes the list
              onMouseDown={(event) => {
                event.preventDefault();
                choose(place);
              }}
            >
              {place.label}
            </li>
          ))}
        </ul>
      )}
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
