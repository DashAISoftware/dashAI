import React, { useState } from "react";
import PropTypes from "prop-types";

import {
  Collapse,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";

import {
  DataObject as DataObjectIcon,
  DataArray as DataArrayIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
} from "@mui/icons-material";

/**
 * Recursive component that transforms the JSON of a object into a nested and expandable list.
 * @param {string} name the name of the current parameter to render as an item
 * @param {object| bool | number| string} value the value of the curent item, it can be the value of the
 * parameter or an object with its own parameters.
 * @param {object} initialState the initial state of the component, it can be used to set the initial
 * state of the nested lists.
 */
function NestedListDisplayer({
  name,
  value,
  initialState = {
    open: false,
  },
}) {
  const [open, setOpen] = useState(initialState.open);

  // configurable object parameter case
  if (value && value.constructor.name === "Object") {
    return (
      <List key={name} dense>
        <ListItemButton onClick={() => setOpen((current) => !current)}>
          <ListItemIcon>
            <DataObjectIcon color="primary" />
          </ListItemIcon>
          <ListItemText>{name}</ListItemText>
          {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </ListItemButton>

        <Collapse in={open} timeout="auto" unmountOnExit>
          <List sx={{ pl: 4 }} dense>
            {Object.keys(value).map((key) => (
              <NestedListDisplayer
                key={`${name}-${key}`}
                name={key}
                value={value[key]}
              />
            ))}
          </List>
        </Collapse>
      </List>
    );
  }

  // array parameter case
  if (Array.isArray(value)) {
    return (
      <List key={name} dense>
        <ListItemButton onClick={() => setOpen((current) => !current)}>
          <ListItemIcon>
            <DataArrayIcon color="primary" />
          </ListItemIcon>
          <ListItemText>{name}</ListItemText>
          {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </ListItemButton>

        <Collapse in={open} timeout="auto" unmountOnExit>
          <List sx={{ pl: 4 }} dense>
            {value.map((item, index) => (
              <NestedListDisplayer
                key={`${name}-${index}`}
                name={item.name || item.key || item.columnName || index}
                value={item}
              />
            ))}
          </List>
        </Collapse>
      </List>
    );
  }

  // simple key-value parameter case
  return (
    <ListItem>
      <ListItemText
        primary={<Typography variant="p">{name + ":"}</Typography>}
        secondary={
          <Typography variant="p" sx={{ ml: 1, color: "gray" }}>
            {typeof value === "boolean"
              ? String(value)
              : value === null
              ? "null"
              : value}
          </Typography>
        }
      />
    </ListItem>
  );
}

NestedListDisplayer.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
    PropTypes.bool,
    PropTypes.object,
    PropTypes.array,
    PropTypes.oneOf([null]),
  ]),
  initialState: PropTypes.shape({
    open: PropTypes.bool,
  }),
};

export default NestedListDisplayer;
