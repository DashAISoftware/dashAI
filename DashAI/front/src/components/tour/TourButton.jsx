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
        sx={{ position: 'fixed', bottom: 20, right: 20, backgroundColor: '#1976d2', color: 'white', '&:hover': { backgroundColor: '#1565c0' }, zIndex: 1000 }}
      >
        <HelpOutlineIcon />
      </IconButton>
    </Tooltip>
  );
};
