import logging
import ast
import re
import numpy as np
import pandas as pd
import pydantic
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def parse_params(model_class, params):
    """
    Parse JSON from string to pydantic model.

    Parameters
    ----------
    model_class : BaseModel
        Pydantic model to parse.
    params : str
        Stringified JSON with parameters.

    Returns
    -------
    BaseModel
        Pydantic model parsed from Stringified JSON.
    """
    try:
        model_instance = model_class.model_validate_json(params)
        return model_instance
    except pydantic.ValidationError as e:
        log.error(e)
        raise HTTPException(
            detail=jsonable_encoder(e.errors()),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from e
    
def parse_string_to_list(string):
    """
    Parse a string to a list.
    """
    no_brackets = re.sub(r"[\[\]\(\)\{\}]", "", string)
    no_double_quotes = re.sub(r'"', '', no_brackets)
    no_quotes = re.sub(r"'", '', no_double_quotes)
    splitted_and_stripped = [item.strip() for item in no_quotes.split(",")]
    return splitted_and_stripped

def parse_string_to_dict(string):
    """
    Parse a string to a dictionary.
    """
    return ast.literal_eval(string)

def cast_float_types(string):
    """
    Cast a string to a numpy float.
    """
    if string == "np.float32":
        return np.float32
    elif string == "np.float64":
        return np.float64
    return string

def cast_numpy_types(string):
    """
    Cast a string to a numpy type.
    """
    if string == "np.int32":
        return np.int32
    elif string == "np.int64":
        return np.int64
    return cast_float_types(string)

def cast_float_and_int_types(string):
    """
    Cast a string to a numpy float.
    """
    if string == "int":
        return int
    else:
        return cast_float_types(string)
    
def cast_nan_or_int_types(string):
    """
    Cast a string to a numpy float.
    """
    if string == "np.nan":
        return np.nan
    elif string == "int":
        return int
    
    return string

def cast_nan_types(string):
    """
    Cast a string to a numpy nan or pandas NA.
    """
    if string == None:
        return np.nan
    elif string == "np.nan":
        return np.nan
    elif string == "pandas.NA":
        return pd.NA
    
    return string

def create_random_state():
    """
    Create a random state using numpy random.
    """
    return np.random.RandomState()
