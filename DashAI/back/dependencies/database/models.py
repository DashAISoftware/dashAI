import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.enums.plugin_tags import PluginTag
from DashAI.back.core.enums.status import (
    ConverterStatus,
    DatafileStatus,
    DatasetStatus,
    ExplainerStatus,
    ExplorerStatus,
    PluginStatus,
    PredictionStatus,
    RunStatus,
)

logger = logging.getLogger(__name__)


naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)
Base = declarative_base(metadata=metadata)


class Folder(Base):
    __tablename__ = "folder"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    datasets: Mapped[List["Dataset"]] = relationship(back_populates="folder")


class Dataset(Base):
    __tablename__ = "dataset"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=True)
    total_columns: Mapped[int] = mapped_column(Integer, nullable=True)
    folder_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("folder.id", ondelete="SET NULL"), nullable=True
    )

    notebooks: Mapped[List["Notebook"]] = relationship(
        cascade="all, delete-orphan", back_populates="dataset"
    )
    model_sessions: Mapped[List["ModelSession"]] = relationship(
        "ModelSession", cascade="all, delete-orphan", back_populates="dataset"
    )
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", cascade="all, delete-orphan", back_populates="dataset"
    )
    folder: Mapped[Optional["Folder"]] = relationship(back_populates="datasets")

    status: Mapped[Enum] = mapped_column(
        Enum(DatasetStatus), nullable=False, default=DatasetStatus.NOT_STARTED
    )

    def set_status_as_delivered(self) -> None:
        """
        Update the status of the dataset to delivered and set last_modified to now.
        """
        self.status = DatasetStatus.DELIVERED
        self.last_modified = datetime.now()

    def set_status_as_started(self) -> None:
        """
        Update the status of the dataset to started and set created to now.
        """
        self.status = DatasetStatus.STARTED
        self.created = datetime.now()
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """
        Update the status of the dataset to finished and set last_modified to now.
        """
        self.status = DatasetStatus.FINISHED
        self.last_modified = datetime.now()
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """
        Update the status of the dataset to error.
        """
        self.status = DatasetStatus.ERROR


class ModelSession(Base):
    __tablename__ = "model_session"
    """
    Table to store all the information about a model session.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    input_columns: Mapped[str] = mapped_column(JSON, nullable=False)
    output_columns: Mapped[str] = mapped_column(JSON, nullable=False)

    # Metrics per split
    train_metrics: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    validation_metrics: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    test_metrics: Mapped[list[str]] = mapped_column(JSON, nullable=True)

    splits: Mapped[str] = mapped_column(JSON, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run", cascade="all, delete-orphan", back_populates="model_session"
    )
    dataset = relationship("Dataset", back_populates="model_sessions")


class Run(Base):
    __tablename__ = "run"
    """
    Table to store all the information about a specific run of a model.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    model_session_id: Mapped[int] = mapped_column(
        ForeignKey("model_session.id", ondelete="CASCADE")
    )
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    # model and parameters
    model_name: Mapped[str] = mapped_column(String)
    parameters: Mapped[JSON] = mapped_column(JSON)
    split_indexes: Mapped[str] = mapped_column(JSON, nullable=True)
    # optimizer
    optimizer_name: Mapped[str] = mapped_column(String)
    optimizer_parameters: Mapped[JSON] = mapped_column(JSON)
    plot_history_path: Mapped[str] = mapped_column(String, nullable=True)
    plot_slice_path: Mapped[str] = mapped_column(String, nullable=True)
    plot_contour_path: Mapped[str] = mapped_column(String, nullable=True)
    plot_importance_path: Mapped[str] = mapped_column(String, nullable=True)
    # goal metrics
    goal_metric: Mapped[str] = mapped_column(String)
    # artifacts
    artifacts: Mapped[str] = mapped_column(JSON, nullable=True)
    # metadata
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    run_path: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[Enum] = mapped_column(
        Enum(RunStatus), nullable=False, default=RunStatus.NOT_STARTED
    )
    delivery_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    model_session = relationship("ModelSession", back_populates="runs")
    predictions = relationship(
        "Prediction", cascade="all, delete-orphan", back_populates="run"
    )
    metrics = relationship("Metric", cascade="all, delete-orphan", back_populates="run")

    def set_status_as_delivered(self) -> None:
        """Update the status of the run to delivered and set delivery_time to now."""
        self.status = RunStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the run to started and set start_time to now."""
        self.status = RunStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the run to finished and set end_time to now."""
        self.status = RunStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the run to error."""
        self.status = RunStatus.ERROR


class Prediction(Base):
    __tablename__ = "prediction"
    """
    Table to store all the information about a specific prediction.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), nullable=True)
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    results_path: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[Enum] = mapped_column(
        Enum(PredictionStatus), nullable=False, default=PredictionStatus.NOT_STARTED
    )
    delivery_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="predictions")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="predictions")

    def set_status_as_delivered(self) -> None:
        """Update the status of the prediction to delivered and set
        delivery_time to now."""
        self.status = PredictionStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the prediction to started and set start_time to now."""
        self.status = PredictionStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the prediction to finished and set end_time to now."""
        self.status = PredictionStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the prediction to error."""
        self.status = PredictionStatus.ERROR


class Metric(Base):
    __tablename__ = "metric"
    """
    Table to store all the information related to a metric
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("run.id", ondelete="CASCADE"), index=True
    )
    split: Mapped[SplitEnum] = mapped_column(Enum(SplitEnum), nullable=False)
    level: Mapped[LevelEnum] = mapped_column(Enum(LevelEnum), nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="metrics")


class Plugin(Base):
    __tablename__ = "plugin"
    """
    Table to store all the information related to a plugin
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    installed_version: Mapped[str] = mapped_column(String, nullable=False)
    lastest_version: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[List["Tag"]] = relationship(
        back_populates="plugin", cascade="all, delete", lazy="selectin"
    )
    status: Mapped[Enum] = mapped_column(
        Enum(PluginStatus), nullable=False, default=PluginStatus.REGISTERED
    )
    summary: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    description_content_type: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )


class Tag(Base):
    __tablename__ = "tag"
    """
    Table to store all the tags related to a plugin
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    plugin: Mapped["Plugin"] = relationship(back_populates="tags")
    plugin_id: Mapped[int] = mapped_column(ForeignKey("plugin.id"))
    name: Mapped[Enum] = mapped_column(Enum(PluginTag), nullable=False)


class GlobalExplainer(Base):
    __tablename__ = "global_explainer"
    """
    Table to store all the information about a global explainer.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    run_id: Mapped[int] = mapped_column(nullable=False)
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    explainer_name: Mapped[str] = mapped_column(String, nullable=False)
    explanation_path: Mapped[str] = mapped_column(String, nullable=True)
    plot_path: Mapped[str] = mapped_column(String, nullable=True)
    parameters: Mapped[JSON] = mapped_column(JSON)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[Enum] = mapped_column(
        Enum(ExplainerStatus), nullable=False, default=ExplainerStatus.NOT_STARTED
    )

    def set_status_as_delivered(self) -> None:
        """Update the status of the global explainer to delivered and set delivery_time
        to now."""
        self.status = ExplainerStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the global explainer to started and set start_time
        to now."""
        self.status = ExplainerStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the global explainer to finished and set end_time
        to now."""
        self.status = ExplainerStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the global explainer to error."""
        self.status = ExplainerStatus.ERROR


class LocalExplainer(Base):
    __tablename__ = "local_explainer"
    """
    Table to store all the information about a local explainer.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    run_id: Mapped[int] = mapped_column(nullable=False)
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    explainer_name: Mapped[str] = mapped_column(String, nullable=False)
    dataset_id: Mapped[int] = mapped_column(nullable=False)
    explanation_path: Mapped[str] = mapped_column(String, nullable=True)
    plots_path: Mapped[str] = mapped_column(String, nullable=True)
    parameters: Mapped[JSON] = mapped_column(JSON)
    fit_parameters: Mapped[JSON] = mapped_column(JSON)
    scope: Mapped[JSON] = mapped_column(JSON)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[Enum] = mapped_column(
        Enum(ExplainerStatus), nullable=False, default=ExplainerStatus.NOT_STARTED
    )

    def set_status_as_delivered(self) -> None:
        """Update the status of the local explainer to delivered and set delivery_time
        to now.
        """
        self.status = ExplainerStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the local explainer to started and set start_time
        to now.
        """
        self.status = ExplainerStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the local explainer to finished and set end_time
        to now.
        """
        self.status = ExplainerStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the local explainer to error."""
        self.status = ExplainerStatus.ERROR


class GenerativeProcess(Base):
    __tablename__ = "generative_process"
    """
    Table to store all the information about a specific process of a generative model.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    # metadata
    session_id: Mapped[int] = mapped_column(
        ForeignKey("generative_session.id", ondelete="CASCADE")
    )
    status: Mapped[Enum] = mapped_column(
        Enum(RunStatus), nullable=False, default=RunStatus.NOT_STARTED
    )
    delivery_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    session = relationship("GenerativeSession", back_populates="processes")
    input = relationship(
        "ProcessData",
        primaryjoin=(
            "and_("
            "GenerativeProcess.id == ProcessData.process_id, "
            "ProcessData.is_input == True)"
        ),
        lazy="selectin",
        overlaps="output,process",
    )
    output = relationship(
        "ProcessData",
        primaryjoin=(
            "and_("
            "GenerativeProcess.id == ProcessData.process_id, "
            "ProcessData.is_input == False)"
        ),
        lazy="selectin",
        overlaps="input,process",
    )

    def set_status_as_delivered(self) -> None:
        """
        Update the status of the run to delivered and set delivery_time
        to now.
        """
        self.status = RunStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the process to started and set start_time to now."""
        self.status = RunStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the process to finished and set end_time to now."""
        self.status = RunStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the process to error."""
        self.status = RunStatus.ERROR


class ProcessData(Base):
    __tablename__ = "process_data"
    """
    Base table to store the data of a generative process.
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[str] = mapped_column(String, nullable=False)
    data_type: Mapped[str] = mapped_column(String, nullable=False)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("generative_process.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_input: Mapped[bool] = mapped_column(Boolean, default=True)

    process = relationship(
        "GenerativeProcess", foreign_keys=[process_id], overlaps="input,output"
    )


class GenerativeSession(Base):
    __tablename__ = "generative_session"
    """
    Table to store all the information about a specific session of a generative model.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    # task name
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    # model and parameters
    model_name: Mapped[str] = mapped_column(String)
    parameters: Mapped[JSON] = mapped_column(JSON)
    # metadata
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    # Relationship with GenerativeSessionParameterHistory
    parameters_history: Mapped[List["GenerativeSessionParameterHistory"]] = (
        relationship(
            "GenerativeSessionParameterHistory",
            cascade="all, delete-orphan",
            back_populates="session",
        )
    )

    # Relationship with GenerativeProcess
    processes: Mapped[List["GenerativeProcess"]] = relationship(
        "GenerativeProcess", cascade="all, delete-orphan", back_populates="session"
    )


class Pipeline(Base):
    __tablename__ = "pipeline"
    """
    Table to store all the information about a pipeline.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    edges: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    exploration: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    train: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    prediction: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)


class Converter(Base):
    __tablename__ = "converter"
    """
    Table to store a list of converters applied to a dataset.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(
        ForeignKey("notebook.id", ondelete="CASCADE")
    )
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    converter: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[JSON] = mapped_column(JSON)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    status: Mapped[Enum] = mapped_column(
        Enum(ConverterStatus),
        nullable=False,
        default=ConverterStatus.NOT_STARTED,
    )
    delivery_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Relationships
    notebook: Mapped["Notebook"] = relationship(back_populates="converters")

    def set_status_as_delivered(self) -> None:
        """Update the status of the list to delivered and set delivery_time
        to now.
        """
        self.status = ConverterStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the list to started and set start_time
        to now.
        """
        self.status = ConverterStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the list to finished and set end_time
        to now.
        """
        self.status = ConverterStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the list to error."""
        self.status = ConverterStatus.ERROR


class Notebook(Base):
    __tablename__ = "notebook"
    """
    Table to store all the information about a notebook.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE")
    )
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships
    explorers: Mapped[List["Explorer"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    converters: Mapped[List["Converter"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    dataset: Mapped["Dataset"] = relationship(back_populates="notebooks")


class GenerativeSessionParameterHistory(Base):
    __tablename__ = "parameter_history"
    """
    Table to store the parameters of a generative session and their
    modification history.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("generative_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameters: Mapped[JSON] = mapped_column(JSON, nullable=False)
    modified_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    # Relationship with GenerativeSession
    session = relationship(
        "GenerativeSession",
        back_populates="parameters_history",
        cascade="all, delete",
    )


class Explorer(Base):
    __tablename__ = "explorer"
    """
    Table to store all the information about a explorer.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(
        ForeignKey("notebook.id", ondelete="CASCADE")
    )
    huey_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    # explorer
    columns: Mapped[JSON] = mapped_column(JSON, nullable=False)
    exploration_type: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[JSON] = mapped_column(JSON, nullable=False)
    exploration_path: Mapped[str] = mapped_column(String, nullable=True)
    # Metadata
    name: Mapped[str] = mapped_column(String, nullable=True)

    delivery_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    status: Mapped[Enum] = mapped_column(
        Enum(ExplorerStatus), nullable=False, default=ExplorerStatus.NOT_STARTED
    )
    # Relationships
    notebook: Mapped["Notebook"] = relationship(back_populates="explorers")

    def set_status_as_delivered(self) -> None:
        """Update the status to delivered and set delivery_time to now."""
        self.status = ExplorerStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status to started and set start_time to now."""
        self.status = ExplorerStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status to finished and set end_time to now."""
        self.status = ExplorerStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status to error."""
        self.status = ExplorerStatus.ERROR

    def delete_result(self) -> None:
        """Delete the result of the explorer."""
        if self.exploration_path is not None:
            path = pathlib.Path(self.exploration_path)
            if path.exists():
                if path.is_dir():
                    if len(list(path.iterdir())) == 0:
                        path.rmdir()
                    else:
                        raise FileExistsError(
                            f"Error deleting the exploration result, "
                            f"directory {path} is not empty."
                        )
                else:
                    path.unlink()

            self.exploration_path = None
            self.status = ExplorerStatus.NOT_STARTED
            self.delivery_time = None
            self.start_time = None
            self.end_time = None


class Datafile(Base):
    __tablename__ = "datafile"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    dataset_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    local_path: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[Enum] = mapped_column(
        Enum(DatafileStatus),
        nullable=False,
        default=DatafileStatus.DOWNLOADING,
    )
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "dataset_id",
            name="uq_datafile_source_dataset",
        ),
    )
