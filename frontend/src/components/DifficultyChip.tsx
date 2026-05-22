import React from 'react';
import { Chip, Tooltip } from '@mui/material';

interface Props {
  value: number | null;
  peers: Array<number | null>;
}

/**
 * Relative difficulty chip based on `avg_attempts` (mean attempts-to-first-solve).
 * Buckets the value into thirds of its peer group:
 *   - bottom third → "Easier"  (green)
 *   - middle third → "Average" (grey)
 *   - top third    → "Harder"  (red)
 *
 * Returns null if there's no value or fewer than 2 non-null peers.
 */
const DifficultyChip: React.FC<Props> = ({ value, peers }) => {
  if (value == null) return null;

  const peerValues = peers
    .filter((v): v is number => v !== null)
    .sort((a, b) => a - b);

  if (peerValues.length < 2) return null;

  const leq = peerValues.filter((v) => v <= value).length;
  const pos = leq / peerValues.length;

  let label: string;
  let color: 'success' | 'default' | 'error';
  if (pos <= 1 / 3) {
    label = 'Easier';
    color = 'success';
  } else if (pos > 2 / 3) {
    label = 'Harder';
    color = 'error';
  } else {
    label = 'Average';
    color = 'default';
  }

  return (
    <Tooltip title={`avg ${value.toFixed(2)} attempts to solve, compared to ${peerValues.length - 1} sibling${peerValues.length - 1 === 1 ? '' : 's'}`}>
      <Chip label={label} color={color} size="small" variant="outlined" />
    </Tooltip>
  );
};

export default DifficultyChip;
