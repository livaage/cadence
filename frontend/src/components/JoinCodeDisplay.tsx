import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { Button, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';

interface Props {
  joinCode: string;
  contextName?: string;
  size?: 'small' | 'medium';
}

/**
 * Button + fullscreen overlay so a teacher can project the join code
 * for students to type into `%cadence_session`.
 *
 * Implemented as a portal'd plain div (not MUI Modal/Dialog) — those layers
 * kept interfering with the click-anywhere-to-close UX. With a raw div the
 * onClick is on the outermost element you can see; nothing intercepts.
 */
const JoinCodeDisplay: React.FC<Props> = ({ joinCode, contextName, size = 'small' }) => {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    // Stop the page scrolling behind the overlay
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  const overlay = open ? ReactDOM.createPortal(
    <div
      onClick={() => setOpen(false)}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: '#0d47a1',
        color: 'white',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
        boxSizing: 'border-box',
        zIndex: 99999,
      }}
    >
      <IconButton
        onClick={(e) => { e.stopPropagation(); setOpen(false); }}
        aria-label="Close"
        sx={{
          position: 'absolute', top: 16, right: 16, color: 'white',
          bgcolor: 'rgba(255,255,255,0.1)',
          '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
        }}
      >
        <CloseIcon />
      </IconButton>
      {contextName && (
        <div
          style={{
            fontSize: 'clamp(1.2rem, 3vw, 2rem)',
            opacity: 0.85,
            marginBottom: 28,
            textAlign: 'center',
          }}
        >
          Join code for <strong>{contextName}</strong>
        </div>
      )}
      <div
        style={{
          fontFamily: '"JetBrains Mono", "Menlo", monospace',
          fontSize: 'clamp(4rem, 18vw, 10rem)',
          fontWeight: 700,
          letterSpacing: '0.04em',
          lineHeight: 1.05,
          wordBreak: 'break-all',
          textAlign: 'center',
        }}
      >
        {joinCode}
      </div>
      <div
        style={{
          marginTop: 36,
          fontSize: 'clamp(0.9rem, 1.5vw, 1.25rem)',
          opacity: 0.85,
          textAlign: 'center',
          maxWidth: '90vw',
        }}
      >
        Run in a notebook:{' '}
        <code
          style={{
            backgroundColor: 'rgba(255,255,255,0.15)',
            padding: '6px 12px',
            borderRadius: 4,
            display: 'inline-block',
            marginTop: 8,
            fontFamily: '"JetBrains Mono", "Menlo", monospace',
          }}
        >
          %cadence_session {joinCode} "your-name"
        </code>
      </div>
      <div style={{ marginTop: 36, fontSize: '0.85rem', opacity: 0.55 }}>
        Click anywhere or press Esc to close
      </div>
    </div>,
    document.body,
  ) : null;

  return (
    <>
      <Button
        size={size}
        variant="outlined"
        startIcon={<OpenInFullIcon fontSize="small" />}
        onClick={() => setOpen(true)}
        sx={{ textTransform: 'none' }}
      >
        Display join code
      </Button>
      {overlay}
    </>
  );
};

export default JoinCodeDisplay;
