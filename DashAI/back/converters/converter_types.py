from DashAI.back.types.value_types import (
    Text,
    Integer,
    Float,
    Time,
    Timestamp,
    Duration,
    Decimal,
    Date,
    Binary,
)
from DashAI.back.types.categorical import Categorical
import pyarrow as pa

SKLEARN_CONVERTERS_TYPES = {
    "AdditiveChi2Sampler": Float(arrow_type=pa.float64()),
    "Binarizer": Integer(arrow_type=pa.int64()),
    "CCA": Float(arrow_type=pa.float64()),
    "FastICA": Float(arrow_type=pa.float64()),
    "IncrementalPCA": Float(arrow_type=pa.float64()),
    "KNNImputer": Float(arrow_type=pa.float64()),
    "LabelBinarizer": Integer(arrow_type=pa.int64()),
    "LabelEncoder": Categorical(values=pa.array(["0", "1"])), #Placeholder for initialization
    "MaxAbsScaler": Float(arrow_type=pa.float64()),
    "MinMaxScaler": Float(arrow_type=pa.float64()),
    "MissingIndicator": Integer(arrow_type=pa.int64()),
    "Normalizer": Float(arrow_type=pa.float64()),
    "Nystroem": Float(arrow_type=pa.float64()),
    "OneHotEncoder": Integer(arrow_type=pa.int64()),
    "OrdinalEncoder": Categorical(values=pa.array(["0", "1"])),  # Placeholder for initialization
    "PCA": Float(arrow_type=pa.float64()),
    "PolynomialFeatures": Float(arrow_type=pa.float64()),
    "RBFSampler": Float(arrow_type=pa.float64()),
    "SelectFdr": Float(arrow_type=pa.float64()),
    "SelectFpr": Float(arrow_type=pa.float64()),
    "SelectFwe": Float(arrow_type=pa.float64()),
    "SelectKBest": Float(arrow_type=pa.float64()),
    "SelectPercentile": Float(arrow_type=pa.float64()),
    "SimpleImputer": Float(arrow_type=pa.float64()),
    "SkewedChi2Sampler": Float(arrow_type=pa.float64()),
    "StandardScaler": Float(arrow_type=pa.float64()),
    "TruncatedSVD": Float(arrow_type=pa.float64()),
    "VarianceThreshold": Float(arrow_type=pa.float64()),
    
}

HF_CONVERTERS_TYPES = {
    "Embedding": Float(arrow_type=pa.float32()),
}

IMBALANCED_LEARN_CONVERTERS_TYPES = {
    

}