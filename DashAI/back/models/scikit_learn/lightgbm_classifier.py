from lightgbm import LGBMClassifier as _LGBMClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class LGBMClassifierSchema(BaseSchema):
    """Schema that configures the LightGBM Classifier.

    LightGBM is a gradient boosting ensemble method that grows trees
    leaf-wise (best-first) rather than level-wise, using histogram-based
    splitting to reach high accuracy with fast training on large tabular
    datasets. The underlying implementation is ``lightgbm.LGBMClassifier``.
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
    num_leaves: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 31,
            "lower_bound": 8,
            "upper_bound": 128,
        },
        description=MultilingualString(
            en=(
                "The maximum number of leaves per tree. This is LightGBM's main "
                "capacity control, since it grows trees leaf-wise rather than "
                "level-wise. Must be an integer greater than 1."
            ),
            es=(
                "El número máximo de hojas por árbol. Este es el principal "
                "control de capacidad de LightGBM, ya que construye árboles hoja "
                "por hoja en lugar de nivel por nivel. Debe ser un entero mayor a 1."
            ),
            pt=(
                "O número máximo de folhas por árvore. Este é o principal "
                "controle de capacidade do LightGBM, já que ele constrói árvores "
                "folha a folha em vez de nível a nível. Deve ser um inteiro maior "
                "que 1."
            ),
            de=(
                "Die maximale Anzahl von Blättern pro Baum. Dies ist die "
                "wichtigste Kapazitätskontrolle von LightGBM, da es Bäume "
                "blattweise statt ebenenweise aufbaut. Muss eine ganze Zahl "
                "größer als 1 sein."
            ),
            zh="每棵树的最大叶节点数。这是LightGBM的主要容量控制参数，因为它是逐叶而非逐层生长树的。必须为大于1的整数。",
        ),
        alias=MultilingualString(
            en="Num leaves",
            es="Número de hojas",
            pt="Número de folhas",
            de="Anzahl der Blätter",
            zh="叶节点数量",
        ),
    )  # type: ignore
    learning_rate: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.1,
            "lower_bound": 0.01,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Step size shrinkage applied to each tree's contribution. Lower "
                "values need more estimators but generalise better."
            ),
            es=(
                "Reducción del tamaño de paso aplicada a la contribución de cada "
                "árbol. Valores menores requieren más estimadores pero generalizan "
                "mejor."
            ),
            pt=(
                "Redução do tamanho do passo aplicada à contribuição de cada "
                "árvore. Valores menores exigem mais estimadores, mas generalizam "
                "melhor."
            ),
            de=(
                "Schrittweitenreduktion, die auf den Beitrag jedes Baums "
                "angewendet wird. Kleinere Werte benötigen mehr Schätzer, "
                "generalisieren aber besser."
            ),
            zh="应用于每棵树贡献的步长收缩。较小的值需要更多的估计器，但泛化效果更好。",
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
                "Fraction of training samples randomly drawn to grow each tree "
                "(bagging fraction). Values below 1.0 introduce randomness that "
                "helps prevent overfitting."
            ),
            es=(
                "Fracción de muestras de entrenamiento tomadas aleatoriamente para "
                "construir cada árbol (bagging fraction). Valores menores a 1.0 "
                "introducen aleatoriedad que ayuda a prevenir el sobreajuste."
            ),
            pt=(
                "Fração de amostras de treinamento sorteadas aleatoriamente para "
                "construir cada árvore (bagging fraction). Valores abaixo de 1.0 "
                "introduzem aleatoriedade que ajuda a prevenir o overfitting."
            ),
            de=(
                "Anteil der Trainingsstichproben, die zufällig zum Aufbau jedes "
                "Baums gezogen werden (Bagging-Anteil). Werte unter 1,0 führen "
                "Zufälligkeit ein, die Overfitting vorbeugt."
            ),
            zh="随机抽取用于构建每棵树的训练样本比例（bagging比例）。小于1.0的值会引入随机性，有助于防止过拟合。",
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
            "fixed_value": 0.0,
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
    min_child_samples: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 20,
            "lower_bound": 5,
            "upper_bound": 50,
        },
        description=MultilingualString(
            en=(
                "The minimum number of samples required in a leaf. LightGBM's "
                "main safeguard against overfitting on small datasets, since it "
                "grows trees leaf-wise."
            ),
            es=(
                "El número mínimo de muestras requeridas en una hoja. La "
                "principal salvaguarda de LightGBM contra el sobreajuste en "
                "conjuntos de datos pequeños, ya que construye árboles hoja por "
                "hoja."
            ),
            pt=(
                "O número mínimo de amostras necessárias em uma folha. A "
                "principal salvaguarda do LightGBM contra o overfitting em "
                "conjuntos de dados pequenos, já que ele constrói árvores folha a "
                "folha."
            ),
            de=(
                "Die Mindestanzahl von Stichproben, die in einem Blatt "
                "erforderlich sind. Die wichtigste Absicherung von LightGBM gegen "
                "Overfitting bei kleinen Datensätzen, da es Bäume blattweise "
                "aufbaut."
            ),
            zh="叶节点所需的最小样本数。这是LightGBM在小数据集上防止过拟合的主要保障，因为它是逐叶生长树的。",
        ),
        alias=MultilingualString(
            en="Min child samples",
            es="Muestras mínimas por hoja",
            pt="Amostras mínimas por folha",
            de="Minimale Stichproben pro Blatt",
            zh="最小叶节点样本数",
        ),
    )  # type: ignore
    class_weight: schema_field(
        none_type(enum_field(enum=["balanced"])),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Weights associated with classes, used to correct for class "
                "imbalance. 'balanced' automatically adjusts weights inversely "
                "proportional to class frequencies. Use None for no weighting. "
                "Only applies to multiclass problems, or binary problems where "
                "``is_unbalance``/``scale_pos_weight`` is not set."
            ),
            es=(
                "Pesos asociados a las clases, usados para corregir el desbalance "
                "de clases. 'balanced' ajusta automáticamente los pesos de forma "
                "inversamente proporcional a la frecuencia de cada clase. Use None "
                "para no aplicar ponderación. Solo aplica a problemas "
                "multiclase, o binarios en los que no se haya configurado "
                "``is_unbalance``/``scale_pos_weight``."
            ),
            pt=(
                "Pesos associados às classes, usados para corrigir o "
                "desbalanceamento de classes. 'balanced' ajusta automaticamente os "
                "pesos de forma inversamente proporcional à frequência de cada "
                "classe. Use None para não aplicar ponderação. Aplica-se apenas a "
                "problemas multiclasse, ou binários em que ``is_unbalance``/"
                "``scale_pos_weight`` não estejam definidos."
            ),
            de=(
                "Gewichte, die den Klassen zugeordnet sind, um "
                "Klassenungleichgewichte auszugleichen. 'balanced' passt die "
                "Gewichte automatisch umgekehrt proportional zur "
                "Klassenhäufigkeit an. Verwenden Sie None für keine Gewichtung. "
                "Gilt nur für Mehrklassenprobleme oder binäre Probleme, bei "
                "denen ``is_unbalance``/``scale_pos_weight`` nicht gesetzt ist."
            ),
            zh=(
                "与类别关联的权重，用于纠正类别不平衡。'balanced'会根据类别频率的"
                "反比自动调整权重。使用None表示不加权。仅适用于多分类问题，"
                "或未设置``is_unbalance``/``scale_pos_weight``的二分类问题。"
            ),
        ),
        alias=MultilingualString(
            en="Class weight",
            es="Peso de clase",
            pt="Peso da classe",
            de="Klassengewicht",
            zh="类别权重",
        ),
    )  # type: ignore


class _LightGBMDashAIMixin(TabularClassificationModel, SklearnLikeClassifier):
    """Combines DashAI's two mixins into a single class.

    ``lightgbm.LGBMModel.get_params()`` does not use cooperative ``super()``
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


class LGBMClassifier(_LightGBMDashAIMixin, _LGBMClassifier):
    """LightGBM gradient boosting classifier for tabular data.

    LightGBM grows trees leaf-wise (choosing the leaf with the largest loss
    reduction at each step) instead of level-wise, combined with
    histogram-based feature binning, which typically yields faster training
    and lower memory usage than level-wise boosting methods on large tabular
    datasets, at the cost of being more prone to overfitting on small ones
    (mitigated via ``num_leaves`` and ``min_child_samples``).

    Key hyperparameters include ``n_estimators`` (number of boosting rounds),
    ``num_leaves``, ``learning_rate``, ``subsample``, ``colsample_bytree``,
    ``reg_alpha``, ``reg_lambda``, and ``min_child_samples``. The
    implementation wraps ``lightgbm.LGBMClassifier``.

    References
    ----------
    - [1] Ke, G. et al. (2017). "LightGBM: A Highly Efficient Gradient
           Boosting Decision Tree." Advances in Neural Information Processing
           Systems 30.
           https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html
    - [2] https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMClassifier.html
    """

    SCHEMA = LGBMClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="LightGBM",
        es="LightGBM",
        pt="LightGBM",
        de="LightGBM",
        zh="LightGBM",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Fast, leaf-wise gradient boosting framework optimized for large "
            "tabular datasets."
        ),
        es=(
            "Marco de gradient boosting rápido y hoja por hoja, optimizado para "
            "conjuntos de datos tabulares grandes."
        ),
        pt=(
            "Framework de gradient boosting rápido e folha a folha, otimizado "
            "para conjuntos de dados tabulares grandes."
        ),
        de=(
            "Schnelles, blattweises Gradient-Boosting-Framework, optimiert für "
            "große tabellarische Datensätze."
        ),
        zh="快速的逐叶生长梯度提升框架，针对大型表格数据集进行了优化。",
    )
    COLOR: str = "#7986CB"
    ICON: str = "FlashOn"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent LightGBM wrapper.
            See the associated schema class for available keys and their
            defaults.
        """
        # LightGBM only applies `subsample` (bagging_fraction) when
        # `subsample_freq` (bagging_freq) is > 0; its own default is 0, which
        # would silently turn the schema's `subsample` field into a no-op.
        kwargs["subsample_freq"] = 1
        # Silence the per-iteration [LightGBM] Info/Warning banner, which
        # would otherwise spam the Huey worker process logs.
        kwargs["verbose"] = -1
        kwargs["n_jobs"] = 1
        super().__init__(**kwargs)
