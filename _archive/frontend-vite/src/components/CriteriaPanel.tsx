import type { Criteria, Meta, Weights } from "../types";

const WEIGHT_LABELS: Record<keyof Weights, string> = {
  distance: "Distance",
  recency: "Sale recency",
  living_area: "Living area",
  beds: "Bedrooms",
  baths: "Bathrooms",
  lot_size: "Lot size",
  age: "Year built",
  style: "Style",
  condition: "Assessor condition & grade",
  features: "Basement / fireplace / garage",
};

interface Props {
  criteria: Criteria;
  meta: Meta;
  onChange: (c: Criteria) => void;
  onReset: () => void;
}

export function CriteriaPanel({ criteria: c, meta, onChange, onReset }: Props) {
  const set = (patch: Partial<Criteria>) => onChange({ ...c, ...patch });
  const allValidity = [...meta.validity_options.default, ...meta.validity_options.optional];
  return (
    <div className="panel-body">
      <fieldset className="form-grid">
        <legend>Eligibility rules</legend>
        <label>
          Radius (miles)
          <input type="number" min={0.1} max={10} step={0.1} value={c.max_distance_miles}
            onChange={(e) => set({ max_distance_miles: Number(e.target.value) || 1 })} />
        </label>
        <label>
          Look-back (months)
          <input type="number" min={1} max={60} value={c.lookback_months}
            onChange={(e) => set({ lookback_months: Number(e.target.value) || 12 })} />
        </label>
        <label>
          Comps to select
          <input type="number" min={1} max={25} value={c.max_results}
            onChange={(e) => set({ max_results: Number(e.target.value) || 5 })} />
        </label>
        <label>
          Minimum comps
          <input type="number" min={1} max={10} value={c.min_comps}
            onChange={(e) => set({ min_comps: Number(e.target.value) || 3 })} />
        </label>
        <label>
          Living-area tolerance ±%
          <input type="number" min={5} max={200} value={c.living_area_tolerance_pct ?? ""} placeholder="any"
            onChange={(e) => set({ living_area_tolerance_pct: e.target.value === "" ? null : Number(e.target.value) })} />
        </label>
        <label>
          Minimum price ($)
          <input type="number" min={0} step={1000} value={c.min_price}
            onChange={(e) => set({ min_price: Number(e.target.value) || 0 })} />
        </label>
        <label className="check">
          <input type="checkbox" checked={c.same_property_type} onChange={(e) => set({ same_property_type: e.target.checked })} />
          Same property type only
        </label>
        <label className="check">
          <input type="checkbox" checked={c.exclude_multi_parcel} onChange={(e) => set({ exclude_multi_parcel: e.target.checked })} />
          Exclude multi-parcel deeds
        </label>
      </fieldset>
      <fieldset>
        <legend>County sale-validity codes accepted</legend>
        {allValidity.map((v) => (
          <label className="check" key={v}>
            <input
              type="checkbox"
              checked={c.allowed_validity.includes(v)}
              onChange={(e) =>
                set({
                  allowed_validity: e.target.checked
                    ? [...c.allowed_validity, v]
                    : c.allowed_validity.filter((x) => x !== v),
                })
              }
            />
            {v}
          </label>
        ))}
        <p className="muted small">Non-market transfers (no consideration, related parties, foreclosure, etc.) are never eligible.</p>
      </fieldset>
      <fieldset className="form-grid">
        <legend>Ranking weights</legend>
        {(Object.keys(WEIGHT_LABELS) as (keyof Weights)[]).map((k) => (
          <label key={k}>
            {WEIGHT_LABELS[k]}
            <input type="number" min={0} max={100} value={c.weights[k]}
              onChange={(e) => set({ weights: { ...c.weights, [k]: Number(e.target.value) || 0 } })} />
          </label>
        ))}
        <p className="muted small full">
          Each comp's score is the weighted average of the factors that could be compared (0–100). Factors without
          data are left out and listed. Sale price is never a factor.
        </p>
      </fieldset>
      <button type="button" className="secondary" onClick={onReset}>Reset to defaults</button>
    </div>
  );
}
