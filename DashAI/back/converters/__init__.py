# flake8: noqa

# Chain of converters utility
from DashAI.back.converters.scikit_learn.converter_chain import ConverterChain

# Cross decomposition module
from DashAI.back.converters.scikit_learn.cca import CCA

# Decomposition module
from DashAI.back.converters.scikit_learn.fast_ica import FastICA # 422
from DashAI.back.converters.scikit_learn.incremental_pca import IncrementalPCA # 422
from DashAI.back.converters.scikit_learn.pca import PCA # 422
from DashAI.back.converters.scikit_learn.truncated_svd import TruncatedSVD # 422

# Preprocessing module
from DashAI.back.converters.scikit_learn.binarizer import Binarizer
from DashAI.back.converters.scikit_learn.k_bins_discretizer import KBinsDiscretizer # 422
from DashAI.back.converters.scikit_learn.label_binarizer import LabelBinarizer # takes 2 but 3 were given
from DashAI.back.converters.scikit_learn.label_encoder import LabelEncoder # takes 2 but 3 were given
from DashAI.back.converters.scikit_learn.max_abs_scaler import MaxAbsScaler
from DashAI.back.converters.scikit_learn.min_max_scaler import MinMaxScaler
from DashAI.back.converters.scikit_learn.multi_label_binarizer import (
    MultiLabelBinarizer,
)
from DashAI.back.converters.scikit_learn.normalizer import Normalizer
from DashAI.back.converters.scikit_learn.one_hot_encoder import OneHotEncoder # 422
from DashAI.back.converters.scikit_learn.ordinal_encoder import OrdinalEncoder # 422
from DashAI.back.converters.scikit_learn.polynomial_features import PolynomialFeatures
from DashAI.back.converters.scikit_learn.standard_scaler import StandardScaler

# Feature extraction from text module
from DashAI.back.converters.scikit_learn.count_vectorizer import CountVectorizer # 422
from DashAI.back.converters.scikit_learn.hashing_vectorizer import HashingVectorizer # 422
from DashAI.back.converters.scikit_learn.tfidf_vectorizer import TfidfVectorizer # 422

# Feature selection module
from DashAI.back.converters.scikit_learn.generic_univariate_select import (
    GenericUnivariateSelect,
)
from DashAI.back.converters.scikit_learn.select_percentile import SelectPercentile
from DashAI.back.converters.scikit_learn.select_k_best import SelectKBest
from DashAI.back.converters.scikit_learn.select_fpr import SelectFpr
from DashAI.back.converters.scikit_learn.select_fdr import SelectFdr
from DashAI.back.converters.scikit_learn.select_fwe import SelectFwe
from DashAI.back.converters.scikit_learn.variance_threshold import VarianceThreshold

# Impute module
from DashAI.back.converters.scikit_learn.simple_imputer import SimpleImputer # 422
from DashAI.back.converters.scikit_learn.missing_indicator import MissingIndicator # 422
from DashAI.back.converters.scikit_learn.knn_imputer import KNNImputer # 422

# Kernel approximation module
from DashAI.back.converters.scikit_learn.additive_chi_2_sampler import (
    AdditiveChi2Sampler, # 422
)
from DashAI.back.converters.scikit_learn.nystroem import Nystroem # 422
from DashAI.back.converters.scikit_learn.rbf_sampler import RBFSampler # 422
from DashAI.back.converters.scikit_learn.skewed_chi_2_sampler import SkewedChi2Sampler # 422

# Hugging Face module
from DashAI.back.converters.hugging_face.embedding import Embedding