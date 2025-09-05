import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from DashAI.back.core.enums.plugin_tags import PluginTag
from DashAI.back.core.enums.status import (
    ConverterListStatus,
    ExplainerStatus,
    ExplorerStatus,
    PluginStatus,
    RunStatus,
)

logger = logging.getLogger(__name__)


Base = declarative_base()


class Dataset(Base):
    __tablename__ = "dataset"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    notebooks: Mapped[List["Notebook"]] = relationship(
        cascade="all, delete-orphan", back_populates="dataset"
    )
    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment", cascade="all, delete-orphan", back_populates="dataset"
    )


class Experiment(Base):
    __tablename__ = "experiment"
    """
    Table to store all the information about a model.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    input_columns: Mapped[str] = mapped_column(JSON, nullable=False)
    output_columns: Mapped[str] = mapped_column(JSON, nullable=False)
    splits: Mapped[str] = mapped_column(JSON, nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run", cascade="all, delete-orphan", back_populates="experiment"
    )
    dataset = relationship("Dataset", back_populates="experiments")


class Run(Base):
    __tablename__ = "run"
    """
    Table to store all the information about a specific run of a model.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiment.id", ondelete="CASCADE")
    )
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
    # metrics
    train_metrics: Mapped[JSON] = mapped_column(JSON, nullable=True)
    test_metrics: Mapped[JSON] = mapped_column(JSON, nullable=True)
    validation_metrics: Mapped[JSON] = mapped_column(JSON, nullable=True)
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
    experiment = relationship("Experiment", back_populates="runs")

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
    explainer_name: Mapped[str] = mapped_column(String, nullable=False)
    dataset_id: Mapped[int] = mapped_column(nullable=False)
    explanation_path: Mapped[str] = mapped_column(String, nullable=True)
    plots_path: Mapped[str] = mapped_column(String, nullable=True)
    parameters: Mapped[JSON] = mapped_column(JSON)
    fit_parameters: Mapped[JSON] = mapped_column(JSON)
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
    name: Mapped[str] = mapped_column(String)
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


class ConverterList(Base):
    __tablename__ = "converter_list"
    """
    Table to store a list of converters applied to a dataset.
    """
    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(
        ForeignKey("notebook.id", ondelete="CASCADE")
    )
    converter: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[JSON] = mapped_column(JSON)
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    last_modified: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    status: Mapped[Enum] = mapped_column(
        Enum(ConverterListStatus),
        nullable=False,
        default=ConverterListStatus.NOT_STARTED,
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
        self.status = ConverterListStatus.DELIVERED
        self.delivery_time = datetime.now()

    def set_status_as_started(self) -> None:
        """Update the status of the list to started and set start_time
        to now.
        """
        self.status = ConverterListStatus.STARTED
        self.start_time = datetime.now()

    def set_status_as_finished(self) -> None:
        """Update the status of the list to finished and set end_time
        to now.
        """
        self.status = ConverterListStatus.FINISHED
        self.end_time = datetime.now()

    def set_status_as_error(self) -> None:
        """Update the status of the list to error."""
        self.status = ConverterListStatus.ERROR


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
    converters: Mapped[List["ConverterList"]] = relationship(
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
