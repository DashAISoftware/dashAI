import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { useTourContext } from './TourProvider';

export const TourButton = ( {tourKey}) => {
  const { resetTour, startTour } = useTourContext();
  return (
    <Tooltip title="Start Tour" placement="left">
      <IconButton
        onClick={() => { resetTour(); startTour(); }} 
          sx={{ 
          position: 'fixed', 
          top: 80, 
          right: 16, 
          backgroundColor: '#1976d2', 
          color: 'white',
          width: 36,
          height: 36,
          '&:hover': { 
            backgroundColor: '#1565c0',
            transform: 'scale(1.05)',
          },
          transition: 'all 0.2s ease-in-out',
          boxShadow: 2,
          zIndex: 1000 
        }}
      >
        <HelpOutlineIcon />
      </IconButton>
    </Tooltip>
  );
};
