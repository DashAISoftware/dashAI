from xgboost import XGBClassifier as _XGBClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class XGBClassifierSchema(BaseSchema):
    """Schema that configures the XGBoost Classifier.

    XGBoost (Extreme Gradient Boosting) is a regularized gradient boosting
    ensemble method that sequentially fits decision trees to the residual
    errors of the previous trees. It is widely used in tabular machine
    learning competitions for its speed and accuracy. The underlying
    implementation is ``xgboost.XGBClassifier``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 10,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en=(
                "The number of boosting rounds, i.e. the number of trees to fit "
                "sequentially. Must be an integer greater than or equal to 1."
            ),
            es=(
                "El número de rondas de boosting, es decir, la cantidad de árboles "
                "que se ajustan secuencialmente. Debe ser un entero mayor o igual a 1."
            ),
            pt=(
                "O número de rodadas de boosting, ou seja, a quantidade de árvores "
                "ajustadas sequencialmente. Deve ser um inteiro maior ou igual a 1."
            ),
            de=(
                "Die Anzahl der Boosting-Runden, d.h. die Anzahl der sequenziell "
                "angepassten Bäume. Muss eine ganze Zahl größer oder gleich 1 sein."
            ),
            zh="提升轮数，即依次拟合的树的数量。必须为大于或等于1的整数。",
        ),
        alias=MultilingualString(
            en="N estimators",
            es="N estimadores",
            pt="N estimadores",
            de="Anzahl Schätzer",
            zh="估计器数量",
        ),
    )  # type: ignore
    max_depth: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 6,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "The maximum depth of each tree. Deeper trees model more complex "
                "interactions but are more prone to overfitting."
            ),
            es=(
                "La profundidad máxima de cada árbol. Los árboles más profundos "
                "modelan interacciones más complejas pero son más propensos al "
                "sobreajuste."
            ),
            pt=(
                "A profundidade máxima de cada árvore. Árvores mais profundas "
                "modelam interações mais complexas, mas são mais propensas ao "
                "overfitting."
            ),
            de=(
                "Die maximale Tiefe jedes Baums. Tiefere Bäume modellieren "
                "komplexere Interaktionen, neigen aber eher zu Overfitting."
            ),
            zh="每棵树的最大深度。更深的树能建模更复杂的交互，但更容易过拟合。",
        ),
        alias=MultilingualString(
            en="Max depth",
            es="Profundidad máxima",
            pt="Profundidade máxima",
            de="Maximale Tiefe",
            zh="最大深度",
        ),
    )  # type: ignore
    learning_rate: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.3,
            "lower_bound": 0.01,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Step size shrinkage applied to each tree's contribution, also "
                "known as 'eta'. Lower values need more estimators but generalise "
                "better."
            ),
            es=(
                "Reducción del tamaño de paso aplicada a la contribución de cada "
                "árbol, también conocida como 'eta'. Valores menores requieren más "
                "estimadores pero generalizan mejor."
            ),
            pt=(
                "Redução do tamanho do passo aplicada à contribuição de cada "
                "árvore, também conhecida como 'eta'. Valores menores exigem mais "
                "estimadores, mas generalizam melhor."
            ),
            de=(
                "Schrittweitenreduktion, die auf den Beitrag jedes Baums angewendet "
                "wird, auch als 'eta' bekannt. Kleinere Werte benötigen mehr "
                "Schätzer, generalisieren aber besser."
            ),
            zh="应用于每棵树贡献的步长收缩，也称为'eta'。较小的值需要更多的估计器，但泛化效果更好。",
        ),
        alias=MultilingualString(
            en="Learning rate",
            es="Tasa de aprendizaje",
            pt="Taxa de aprendizado",
            de="Lernrate",
            zh="学习率",
        ),
    )  # type: ignore
    subsample: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.5,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Fraction of training samples randomly drawn to grow each tree. "
                "Values below 1.0 introduce randomness that helps prevent "
                "overfitting."
            ),
            es=(
                "Fracción de muestras de entrenamiento tomadas aleatoriamente para "
                "construir cada árbol. Valores menores a 1.0 introducen aleatoriedad "
                "que ayuda a prevenir el sobreajuste."
            ),
            pt=(
                "Fração de amostras de treinamento sorteadas aleatoriamente para "
                "construir cada árvore. Valores abaixo de 1.0 introduzem "
                "aleatoriedade que ajuda a prevenir o overfitting."
            ),
            de=(
                "Anteil der Trainingsstichproben, die zufällig zum Aufbau jedes "
                "Baums gezogen werden. Werte unter 1,0 führen Zufälligkeit ein, die "
                "Overfitting vorbeugt."
            ),
            zh="随机抽取用于构建每棵树的训练样本比例。小于1.0的值会引入随机性，有助于防止过拟合。",
        ),
        alias=MultilingualString(
            en="Subsample",
            es="Submuestra",
            pt="Subamostra",
            de="Teilstichprobe",
            zh="子采样比例",
        ),
    )  # type: ignore
    colsample_bytree: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.5,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Fraction of features randomly sampled when building each tree. "
                "Values below 1.0 decorrelate the trees, reducing overfitting."
            ),
            es=(
                "Fracción de características muestreadas aleatoriamente al "
                "construir cada árbol. Valores menores a 1.0 decorrelacionan los "
                "árboles, reduciendo el sobreajuste."
            ),
            pt=(
                "Fração de atributos amostrados aleatoriamente ao construir cada "
                "árvore. Valores abaixo de 1.0 descorrelacionam as árvores, "
                "reduzindo o overfitting."
            ),
            de=(
                "Anteil der Merkmale, die zufällig beim Aufbau jedes Baums "
                "ausgewählt werden. Werte unter 1,0 dekorrelieren die Bäume und "
                "verringern Overfitting."
            ),
            zh="构建每棵树时随机采样的特征比例。小于1.0的值可以降低树之间的相关性，减少过拟合。",
        ),
        alias=MultilingualString(
            en="Column subsample by tree",
            es="Submuestra de columnas por árbol",
            pt="Subamostra de colunas por árvore",
            de="Spalten-Teilstichprobe pro Baum",
            zh="每棵树的列子采样比例",
        ),
    )  # type: ignore
    reg_alpha: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 5.0,
        },
        description=MultilingualString(
            en="L1 regularization term on the tree leaf weights. Use 0 for none.",
            es=(
                "Término de regularización L1 sobre los pesos de las hojas del "
                "árbol. Use 0 para no aplicar regularización."
            ),
            pt=(
                "Termo de regularização L1 sobre os pesos das folhas da árvore. "
                "Use 0 para não aplicar regularização."
            ),
            de=(
                "L1-Regularisierungsterm für die Blattgewichte des Baums. "
                "Verwenden Sie 0 für keine Regularisierung."
            ),
            zh="树叶节点权重的L1正则化项。使用0表示不正则化。",
        ),
        alias=MultilingualString(
            en="L1 regularization",
            es="Regularización L1",
            pt="Regularização L1",
            de="L1-Regularisierung",
            zh="L1正则化",
        ),
    )  # type: ignore
    reg_lambda: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.0,
            "upper_bound": 5.0,
        },
        description=MultilingualString(
            en="L2 regularization term on the tree leaf weights. Use 0 for none.",
            es=(
                "Término de regularización L2 sobre los pesos de las hojas del "
                "árbol. Use 0 para no aplicar regularización."
            ),
            pt=(
                "Termo de regularização L2 sobre os pesos das folhas da árvore. "
                "Use 0 para não aplicar regularização."
            ),
            de=(
                "L2-Regularisierungsterm für die Blattgewichte des Baums. "
                "Verwenden Sie 0 für keine Regularisierung."
            ),
            zh="树叶节点权重的L2正则化项。使用0表示不正则化。",
        ),
        alias=MultilingualString(
            en="L2 regularization",
            es="Regularización L2",
            pt="Regularização L2",
            de="L2-Regularisierung",
            zh="L2正则化",
        ),
    )  # type: ignore
    min_child_weight: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=(
                "Minimum sum of instance weight needed in a child node. Larger "
                "values make the algorithm more conservative, helping prevent "
                "overfitting on small partitions."
            ),
            es=(
                "Suma mínima de peso de instancia necesaria en un nodo hijo. "
                "Valores mayores hacen que el algoritmo sea más conservador, "
                "ayudando a prevenir el sobreajuste en particiones pequeñas."
            ),
            pt=(
                "Soma mínima de peso de instância necessária em um nó filho. "
                "Valores maiores tornam o algoritmo mais conservador, ajudando a "
                "prevenir o overfitting em partições pequenas."
            ),
            de=(
                "Minimale Summe des Instanzgewichts, die in einem Kindknoten "
                "benötigt wird. Größere Werte machen den Algorithmus "
                "konservativer und beugen Overfitting bei kleinen Partitionen vor."
            ),
            zh="子节点所需的最小实例权重和。较大的值会使算法更加保守，有助于防止在小分区上过拟合。",
        ),
        alias=MultilingualString(
            en="Min child weight",
            es="Peso mínimo del hijo",
            pt="Peso mínimo do filho",
            de="Minimales Kindgewicht",
            zh="最小子节点权重",
        ),
    )  # type: ignore


class _XGBoostDashAIMixin(TabularClassificationModel, SklearnLikeClassifier):
    """Combines DashAI's two mixins into a single class.

    ``xgboost.XGBModel.get_params()`` does not use cooperative ``super()``
    dispatch; it inspects ``type(self).__bases__`` directly and assumes
    exactly two entries: a mixin without ``get_params`` (normally
    ``ClassifierMixin``) followed by the real estimator class. With three
    separate bases the lookup mis-resolves to a mixin that lacks
    ``get_params`` and raises ``AttributeError``. Folding both DashAI mixins
    into one intermediate class keeps that assumption satisfied.

    Note: this class must not have "Base" in its name — DashAI's
    ``ComponentRegistry._get_base_type`` matches ancestor classes by that
    substring, and a match here would collide with ``BaseModel``.
    """


class XGBClassifier(_XGBoostDashAIMixin, _XGBClassifier):
    """Extreme Gradient Boosting classifier for tabular data.

    XGBoost is a regularized gradient boosting ensemble that sequentially fits
    decision trees to correct the residual errors of the previous trees. It
    combines shrinkage (``learning_rate``), row/column subsampling, and L1/L2
    regularization on leaf weights to control overfitting, and is widely used
    in tabular machine learning competitions for its speed and accuracy.

    Key hyperparameters include ``n_estimators`` (number of boosting rounds),
    ``max_depth``, ``learning_rate``, ``subsample``, ``colsample_bytree``,
    ``reg_alpha``, ``reg_lambda``, and ``min_child_weight``. The implementation
    wraps ``xgboost.XGBClassifier``.

    References
    ----------
    - [1] Chen, T., & Guestrin, C. (2016). "XGBoost: A Scalable Tree Boosting
           System." Proceedings of the 22nd ACM SIGKDD International Conference
           on Knowledge Discovery and Data Mining, 785-794.
           https://doi.org/10.1145/2939672.2939785
    - [2] https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.XGBClassifier
    """

    SCHEMA = XGBClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="XGBoost",
        es="XGBoost",
        pt="XGBoost",
        de="XGBoost",
        zh="XGBoost",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Extreme Gradient Boosting: a fast, regularized tree ensemble widely "
            "used in tabular machine learning competitions."
        ),
        es=(
            "Extreme Gradient Boosting: un ensamble de árboles rápido y "
            "regularizado, ampliamente usado en competencias de aprendizaje "
            "automático tabular."
        ),
        pt=(
            "Extreme Gradient Boosting: um ensemble de árvores rápido e "
            "regularizado, amplamente usado em competições de aprendizado de "
            "máquina tabular."
        ),
        de=(
            "Extreme Gradient Boosting: ein schnelles, regularisiertes "
            "Baum-Ensemble, das häufig in tabellarischen "
            "Machine-Learning-Wettbewerben eingesetzt wird."
        ),
        zh="极端梯度提升：一种快速、正则化的树集成方法，广泛应用于表格化机器学习竞赛。",
    )
    COLOR: str = "#D32F2F"
    ICON: str = "Whatshot"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent XGBoost wrapper.  See
            the associated schema class for available keys and their defaults.
        """
        kwargs["n_jobs"] = 1
        super().__init__(**kwargs)
