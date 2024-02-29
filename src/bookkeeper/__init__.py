"""Python interface for managing simulations."""
import abc
import collections
import configparser
import pathlib
import typing
import warnings
import numpy

SimulationParameter = bool | int | float | str


class ParameterFile(metaclass=abc.ABCMeta):
    """Generic parameter file class using configparser."""

    def __init__(self, path: pathlib.Path):
        """Set the parameter file path and read the file."""
        self.path = path
        self.read()

    @property
    @abc.abstractmethod
    def _quotes_around_string(self) -> bool:
        ...

    @property
    @abc.abstractmethod
    def _true_string(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def _false_string(self) -> str:
        ...

    def __getitem__(self, key: str) -> SimulationParameter:
        """Get simulation parameter."""
        return self.params[key]

    def __setitem__(self, key: str, value: SimulationParameter) -> None:
        """Set simulation parameter."""
        if key not in self.params:
            warnings.warn(f"Key {key} isn't already in configuration file.")
        self.params[key] = value

    def read(self) -> None:
        """Read a parameter file using configparser."""
        self.__conf_parser = configparser.ConfigParser()

        # Read file into configparser, appending a fake section
        with open(self.path, encoding="utf-8") as stream:
            self.__conf_parser.read_string("[main]\n" + stream.read())

        # Copy values into params
        self.params: dict[str, SimulationParameter] = {}
        for key, val in self.__conf_parser["main"].items():
            self.params[key] = self.__convert_to_correct_type(val)

    def __convert_to_correct_type(self, text: str) -> SimulationParameter:
        """Convert configparser strings to the correct type."""
        try:
            val_in_correct_type: SimulationParameter = float(text)
            if float(text) == int(float(text)):
                val_in_correct_type = int(float(text))
        except ValueError:
            val_in_correct_type = text
            if text == self._true_string:
                val_in_correct_type = True
            elif text == self._false_string:
                val_in_correct_type = False
            else:
                if text.startswith("\""):
                    val_in_correct_type = text[1:-1]

        return val_in_correct_type

    def __convert_to_string(self, val: SimulationParameter) -> str:
        """Convert Flash parameter to string for configparser."""
        if isinstance(val, float):
            if val == int(val):
                string = f"{int(val)}"
            else:
                string = f"{val:.15e}"
        elif val is True:
            string = self._true_string
        elif val is False:
            string = self._false_string
        elif isinstance(val, int):
            string = f"{val:d}"
        else:
            if self._quotes_around_string:
                string = f"\"{val}\""
            else:
                string = val

        return string

    def write(self, path: typing.Optional[pathlib.Path] = None) -> None:
        """Write a parameter file using configparser."""
        if path is None:
            path = self.path

        lines = ["=".join([key, self.__convert_to_string(val)])
                 for key, val in self.params.items()]
        text = "\n".join(lines)

        with open(path, "w", encoding="utf-8") as new_config:
            new_config.write(text)


class Simulation(metaclass=abc.ABCMeta):
    """Simulation abstract base class.

    This class only sets its path and reads the parameter file.
    All other attributes are implemented in code-specific simulation
    classes.
    """

    def __init__(self,
                 path: pathlib.Path,
                 par_name: typing.Optional[str] = None
                 ) -> None:
        """Set simulation path and load the folder's parameter file."""
        self.path = path
        if par_name is None:
            self.par = self._parameter_file_type(path / self._default_par_name)
        else:
            self.par = self._parameter_file_type(path / par_name)

    @property
    @abc.abstractmethod
    def _default_par_name(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def complete(self) -> bool:
        ...

    @property
    @abc.abstractmethod
    def reason_incomplete(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def failed(self) -> bool:
        ...

    @abc.abstractmethod
    def run(self, run_command: list[str]) -> None:
        ...

    @property
    @abc.abstractmethod
    def _parameter_file_type(self) -> type:
        ...


class SimulationGrid(metaclass=abc.ABCMeta):
    """A grid of FLASH hydrodynamical simulations."""

    def __init__(
        self,
        paths_to_search: pathlib.Path | collections.abc.Iterable[pathlib.Path]
    ) -> None:
        """Set the root directory."""
        if isinstance(paths_to_search, collections.abc.Iterable):
            self._paths_to_search = paths_to_search
            self.path = None
        else:
            self._paths_to_search = [paths_to_search]
            self.path = paths_to_search

        assert len(self.sims) > 0, "No simulations found!"

    def __iter__(self):
        """Iterate over the grid by iterating over its simulations."""
        return iter(self.sims)

    def __len__(self):
        """Return the number of simulations in the grid."""
        return len(self.sims)

    def __getitem__(self, key):
        """Return the parameter value for each simulation in the grid."""
        return numpy.array([sim.par.params[key] for sim in self.sims])

    @property
    def sims(self) -> list[Simulation]:
        """List of Simulation objects in the grid.

        :return: List of Simulation objects in the grid
        :rtype: typing.List[Simulation]
        """
        return [self._simulation_type(path) for path in self.sim_paths]

    @property
    def failed_sims(self) -> list[Simulation]:
        """List of failed simulations."""
        return [sim for sim in self.sims if sim.failed]

    @property
    def incomplete_sims(self) -> list[Simulation]:
        """List of incomplete simulations."""
        return [sim for sim in self.sims if not sim.complete]

    @property
    def complete_sims(self) -> list[Simulation]:
        """List of incomplete simulations."""
        return [sim for sim in self.sims if sim.complete]

    @property
    def sim_paths(self) -> list[pathlib.Path]:
        """List of simulation paths.

        :return: List of simulation paths
        :rtype: typing.List[pathlib.Path]
        """
        paths: list[pathlib.Path] = []
        for root_path in self._paths_to_search:
            if self._is_sim_folder(root_path):
                paths.append(root_path)
            for path in root_path.rglob("*/"):
                if self._is_sim_folder(path):
                    paths.append(path)
        return paths

    @abc.abstractmethod
    def _is_sim_folder(self, path: pathlib.Path) -> bool:
        ...

    @property
    @abc.abstractmethod
    def _simulation_type(self) -> type:
        ...

    @property
    def complete(self) -> bool:
        """Whether all simulations in the grid are complete.

        :return: Whether all simulations in the grid are complete
        :rtype: bool
        """
        return all(sim.complete for sim in self.sims)
