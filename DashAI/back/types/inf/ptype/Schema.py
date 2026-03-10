# flake8: noqa

import pandas as pd


class Schema:
    def __init__(
        self,
        df,
        cols,
    ):
        self.df = df
        self._cols = cols  # make private so we can document via a property

    _missing_placeholder = "ε"

    @property
    def cols(self):
        """A string-indexed dictionary of Column objects, each containing type information inferred by ptype."""
        return self._cols

    @staticmethod
    def _missing_empty_to_placeholder(str):
        return str if str != "" else Schema._missing_placeholder

    @staticmethod
    def _show_missing_values(xs):
        return list(map(Schema._missing_empty_to_placeholder, xs))

    def show(self):
        """Show the schema, as a dataframe."""
        df = self.df.iloc[0:0, :].copy()
        df.loc[0] = [col.type for _, col in self._cols.items()]
        df.loc[1] = [col.get_normal_values() for _, col in self._cols.items()]
        xss = [col.get_na_values() for _, col in self._cols.items()]
        df.loc[2] = [Schema._show_missing_values(xs) for xs in xss]
        df.loc[3] = [col.get_an_values() for _, col in self._cols.items()]
        placeholders = [Schema._missing_placeholder if "" in xs else "" for xs in xss]

        index = {
            0: "type",
            1: "normal values",
            2: "missing values",
            3: "anomalous values",
        }

        if "".join(placeholders) != "":
            df.loc[4] = placeholders
            index[4] = "(empty string marker)"

        return df.rename(index=index)

    def show_ratios(self):
        """Show ratio of normal, missing as anomalous values, as a dataframe."""
        df = self.df.iloc[0:0, :].copy()
        df.loc[0] = [col.type for _, col in self._cols.items()]
        df.loc[1] = [col.get_normal_ratio() for _, col in self._cols.items()]
        df.loc[2] = [col.get_na_ratio() for _, col in self._cols.items()]
        df.loc[3] = [col.get_an_ratio() for _, col in self._cols.items()]
        return df.rename(
            index={
                0: "type",
                1: "ratio of normal values",
                2: "ratio of missing values",
                3: "ratio of anomalous values",
            }
        )

    def _as_normal(self):
        def as_normal(col):
            vs = self._cols[
                col.name
            ].get_normal_values()  # expensive to recompute inside loop
            return col.map(lambda v: v if v in vs else pd.NA)

        return as_normal

    def transform(self, df):
        """Transform a dataframe according to the schema. The dataframe must be the one used to infer the
        schema, or one structurally similar to it."

         :param df: dataframe to transform.
         :return: Transformed dataframe with appropriately typed columns.
        """
        df = df.apply(self._as_normal(), axis=0)
        ptype_pandas_mapping = {
            "integer": "Int64",
            "date-iso-8601": "datetime64[ms]",
            "date-eu": "datetime64[ms]",
            "date-non-std": "datetime64[ms]",
            "string": "string",
            "boolean": "boolean",  # will remove boolean later
            "float": "float64",
            "time": "time",
        }
        for col_name in df:
            new_dtype = ptype_pandas_mapping[self._cols[col_name].type]
            if new_dtype == "boolean":
                df[col_name] = df[col_name].apply(
                    lambda x: (
                        False if str(x) in ["F"] else (True if str(x) in ["T"] else x)
                    )
                )

            elif new_dtype == "time":
                df[col_name] = pd.to_datetime(
                    df[col_name], format="%H:%M:%S", errors="coerce"
                )
                continue

            try:
                df[col_name] = df[col_name].astype(new_dtype)
            except TypeError:
                # TODO: explain why this case needed
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").astype(
                    new_dtype
                )
        return df
