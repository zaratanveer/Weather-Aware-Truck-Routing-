import { memo, useState, type FormEvent } from 'react';

import { CHECKPOINT_INTERVALS, type CheckpointInterval, type Place, type PlanRequest } from '../api/types';
import { nextFullHour, toDateTimeLocalValue } from '../format';
import { PlaceInput } from './PlaceInput';

// Same limits as the backend (planner/serializers.py).
const MAX_LOAD_LB = 80_000;
const MAX_DAYS_AHEAD = 7;
const HOUR_MS = 60 * 60 * 1000;

interface TripFormProps {
  loading: boolean;
  onSubmit: (request: PlanRequest) => void;
}

type FormErrors = Partial<Record<'origin' | 'destination' | 'departure' | 'load', string>>;

/** memo(): the form doesn't re-render while the heatmap slider moves. */
export const TripForm = memo(function TripForm({ loading, onSubmit }: TripFormProps) {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(() => toDateTimeLocalValue(nextFullHour()));
  const [load, setLoad] = useState('35000');
  const [intervalMiles, setIntervalMiles] = useState<CheckpointInterval>(25);
  const [errors, setErrors] = useState<FormErrors>({});

  function validate(): FormErrors {
    const found: FormErrors = {};
    if (!origin) found.origin = 'Pick a place from the suggestions.';
    if (!destination) found.destination = 'Pick a place from the suggestions.';
    if (origin && destination && origin.lat === destination.lat && origin.lon === destination.lon) {
      found.destination = 'Destination must be different from the origin.';
    }

    const departureTime = new Date(departure).getTime();
    const now = Date.now();
    if (Number.isNaN(departureTime)) found.departure = 'Enter a departure date and time.';
    else if (departureTime < now - HOUR_MS) found.departure = 'Departure cannot be in the past.';
    else if (departureTime > now + MAX_DAYS_AHEAD * 24 * HOUR_MS) {
      found.departure = `Departure must be within ${MAX_DAYS_AHEAD} days (forecast range).`;
    }

    const loadLb = Number(load);
    if (load.trim() === '' || !Number.isFinite(loadLb) || loadLb < 0 || loadLb > MAX_LOAD_LB) {
      found.load = `Enter a load between 0 and ${MAX_LOAD_LB.toLocaleString()} lb.`;
    }
    return found;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0 || !origin || !destination) return;

    onSubmit({
      origin: { lat: origin.lat, lon: origin.lon },
      destination: { lat: destination.lat, lon: destination.lon },
      departure: new Date(departure).toISOString(),
      load_lb: Number(load),
      interval_miles: intervalMiles,
    });
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit} noValidate>
      <PlaceInput
        label="Origin"
        placeholder="e.g. Dallas, TX"
        value={origin}
        onChange={setOrigin}
        error={errors.origin}
      />
      <PlaceInput
        label="Destination"
        placeholder="e.g. Chicago, IL"
        value={destination}
        onChange={setDestination}
        error={errors.destination}
      />

      <div className="field-row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            onChange={(event) => setDeparture(event.target.value)}
            aria-invalid={errors.departure ? true : undefined}
          />
          {errors.departure && <p className="field-error">{errors.departure}</p>}
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={load}
            onChange={(event) => setLoad(event.target.value)}
            aria-invalid={errors.load ? true : undefined}
          />
          {errors.load && <p className="field-error">{errors.load}</p>}
        </div>
      </div>

      <fieldset className="field interval-picker">
        <legend>Weather checkpoint every</legend>
        <div className="segmented">
          {CHECKPOINT_INTERVALS.map((miles) => (
            <label key={miles} className={miles === intervalMiles ? 'segment selected' : 'segment'}>
              <input
                type="radio"
                name="interval"
                value={miles}
                checked={miles === intervalMiles}
                onChange={() => setIntervalMiles(miles)}
              />
              {miles} mi
            </label>
          ))}
        </div>
      </fieldset>

      <button type="submit" className="primary-button" disabled={loading}>
        {loading ? 'Planning routes…' : 'Plan routes'}
      </button>
    </form>
  );
});
