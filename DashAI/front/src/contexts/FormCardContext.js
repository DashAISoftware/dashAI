import React from "react";

/**
 * Context that tells FormInputWrapper (and other low-level inputs) whether they
 * are rendered inside a FormSchemaFieldCard.  When true the tooltip and floating
 * label duplicate information already shown in the card header, so they are hidden.
 */
const FormCardContext = React.createContext(false);

export const useFormCard = () => React.useContext(FormCardContext);

/** Wrap the body of a FormSchemaFieldCard to suppress redundant tooltips/labels */
export const FormCardProvider = ({ children }) => (
  <FormCardContext.Provider value={true}>{children}</FormCardContext.Provider>
);

/** Reset the context for nested sections (e.g. collapse sub-fields) that need their own tooltips */
export const FormCardResetProvider = ({ children }) => (
  <FormCardContext.Provider value={false}>{children}</FormCardContext.Provider>
);
