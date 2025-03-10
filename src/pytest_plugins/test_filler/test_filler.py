"""
Top-level pytest configuration file providing:
- Command-line options,
- Test-fixtures that can be used by all test cases,
and that modifies pytest hooks in order to fill test specs for all tests and
writes the generated fixtures to file.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Type, Union

import pytest

from ethereum_test_forks import Fork
from ethereum_test_tools import (
    BaseTest,
    BaseTestConfig,
    BlockchainTest,
    BlockchainTestFiller,
    Fixture,
    HiveFixture,
    StateTest,
    StateTestFiller,
    Yul,
    fill_test,
)
from evm_transition_tool import TransitionTool
from pytest_plugins.spec_version_checker.spec_version_checker import EIPSpecTestItem


def pytest_addoption(parser):
    """
    Adds command-line options to pytest.
    """
    evm_group = parser.getgroup("evm", "Arguments defining evm executable behavior")
    evm_group.addoption(
        "--evm-bin",
        action="store",
        dest="evm_bin",
        type=Path,
        default=None,
        help=(
            "Path to an evm executable that provides `t8n`. Default: First 'evm' entry in PATH."
        ),
    )
    evm_group.addoption(
        "--traces",
        action="store_true",
        dest="evm_collect_traces",
        default=None,
        help="Collect traces of the execution information from the transition tool.",
    )

    solc_group = parser.getgroup("solc", "Arguments defining the solc executable")
    solc_group.addoption(
        "--solc-bin",
        action="store",
        dest="solc_bin",
        default=None,
        help=(
            "Path to a solc executable (for Yul source compilation). "
            "Default: First 'solc' entry in PATH."
        ),
    )

    test_group = parser.getgroup("tests", "Arguments defining filler location and output")
    test_group.addoption(
        "--filler-path",
        action="store",
        dest="filler_path",
        default="./tests/",
        help="Path to filler directives",
    )
    test_group.addoption(
        "--output",
        action="store",
        dest="output",
        default="./fixtures/",
        help="Directory to store the generated test fixtures. Can be deleted.",
    )
    test_group.addoption(
        "--flat-output",
        action="store_true",
        dest="flat_output",
        default=False,
        help="Output each test case in the directory without the folder structure.",
    )
    test_group.addoption(
        "--enable-hive",
        action="store_true",
        dest="enable_hive",
        default=False,
        help="Output test fixtures with the hive-specific properties.",
    )

    debug_group = parser.getgroup("debug", "Arguments defining debug behavior")
    debug_group.addoption(
        "--t8n-dump-dir",
        action="store",
        dest="t8n_dump_dir",
        default="",
        help="Path to dump the transition tool debug output.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """
    Register the plugin's custom markers and process command-line options.

    Custom marker registration:
    https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#registering-custom-markers
    """
    config.addinivalue_line(
        "markers",
        "state_test: a test case that implement a single state transition test.",
    )
    config.addinivalue_line(
        "markers",
        "blockchain_test: a test case that implements a block transition test.",
    )
    config.addinivalue_line(
        "markers",
        "yul_test: a test case that compiles Yul code.",
    )
    config.addinivalue_line(
        "markers",
        "compile_yul_with(fork): Always compile Yul source using the corresponding evm version.",
    )
    if config.option.collectonly:
        return
    # Instantiate the transition tool here to check that the binary path/trace option is valid.
    # This ensures we only raise an error once, if appropriate, instead of for every test.
    t8n = TransitionTool.from_binary_path(
        binary_path=config.getoption("evm_bin"), trace=config.getoption("evm_collect_traces")
    )
    if (
        isinstance(config.getoption("numprocesses"), int)
        and config.getoption("numprocesses") > 0
        and "Besu" in str(t8n.detect_binary_pattern)
    ):
        pytest.exit(
            "The Besu t8n tool does not work well with the xdist plugin; use -n=0.",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )


@pytest.hookimpl(trylast=True)
def pytest_report_header(config, start_path):
    """Add lines to pytest's console output header"""
    if config.option.collectonly:
        return
    binary_path = config.getoption("evm_bin")
    t8n = TransitionTool.from_binary_path(binary_path=binary_path)
    solc_version_string = Yul("", binary=config.getoption("solc_bin")).version()
    return [f"{t8n.version()}, solc version {solc_version_string}"]


@pytest.fixture(autouse=True, scope="session")
def evm_bin(request) -> Path:
    """
    Returns the configured evm tool binary path.
    """
    return request.config.getoption("evm_bin")


@pytest.fixture(autouse=True, scope="session")
def solc_bin(request):
    """
    Returns the configured solc binary path.
    """
    return request.config.getoption("solc_bin")


@pytest.fixture(autouse=True, scope="session")
def t8n(request, evm_bin: Path) -> Generator[TransitionTool, None, None]:
    """
    Returns the configured transition tool.
    """
    t8n = TransitionTool.from_binary_path(
        binary_path=evm_bin, trace=request.config.getoption("evm_collect_traces")
    )
    yield t8n
    t8n.shutdown()


@pytest.fixture(autouse=True, scope="session")
def base_test_config(request) -> BaseTestConfig:
    """
    Returns the base test configuration that all tests must use.
    """
    config = BaseTestConfig()
    config.enable_hive = request.config.getoption("enable_hive")
    return config


def strip_test_prefix(name: str) -> str:
    """
    Removes the test prefix from a test case name.
    """
    TEST_PREFIX = "test_"
    if name.startswith(TEST_PREFIX):
        return name[len(TEST_PREFIX) :]
    return name


def convert_test_name_to_path(name: str) -> str:
    """
    Converts a test name to a path.
    """
    return re.sub(r"[\[=\-]", "_", name).replace("]", "")


class FixtureCollector:
    """
    Collects all fixtures generated by the test cases.
    """

    all_fixtures: Dict[str, List[Tuple[str, Any]]]
    output_dir: str
    flat_output: bool

    def __init__(self, output_dir: str, flat_output: bool) -> None:
        self.all_fixtures = {}
        self.output_dir = output_dir
        self.flat_output = flat_output

    def add_fixture(self, item, fixture: Optional[Union[Fixture, HiveFixture]]) -> None:
        """
        Adds a fixture to the list of fixtures of a given test case.
        """
        # TODO: remove this logic. if hive enabled set --from to Merge
        if fixture is None:
            return

        def get_module_dir(item) -> str:
            """
            Returns the directory of the test case module.
            """
            dirname = os.path.dirname(item.path)
            basename, _ = os.path.splitext(item.path)
            basename = strip_test_prefix(os.path.basename(basename))
            module_path_no_ext = os.path.join(dirname, basename)
            module_dir = os.path.relpath(
                module_path_no_ext,
                item.funcargs["filler_path"],
            )
            return module_dir

        module_dir = (
            strip_test_prefix(item.originalname)
            if self.flat_output
            else os.path.join(
                get_module_dir(item),
                strip_test_prefix(item.originalname),
            )
        )
        if module_dir not in self.all_fixtures:
            self.all_fixtures[module_dir] = []
        m = re.match(r".*?\[(.*)\]", item.name)
        if not m:
            raise Exception("Could not parse test name: " + item.name)
        name = m.group(1)
        if fixture.name:
            name += "-" + fixture.name
        jsonFixture = fixture.to_json()
        self.all_fixtures[module_dir].append((name, jsonFixture))

    def dump_fixtures(self) -> None:
        """
        Dumps all collected fixtures to their respective files.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        for module_file, fixtures in self.all_fixtures.items():
            output_json = {}
            for index, name_fixture in enumerate(fixtures):
                name, fixture = name_fixture
                name = str(index).zfill(3) + "-" + name
                output_json[name] = fixture
            file_path = os.path.join(self.output_dir, module_file + ".json")
            if not self.flat_output:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(output_json, f, indent=4)


@pytest.fixture(scope="module")
def fixture_collector(request):
    """
    Returns the configured fixture collector instance used for all tests
    in one test module.
    """
    fixture_collector = FixtureCollector(
        output_dir=request.config.getoption("output"),
        flat_output=request.config.getoption("flat_output"),
    )
    yield fixture_collector
    fixture_collector.dump_fixtures()


@pytest.fixture(autouse=True, scope="session")
def engine():
    """
    Returns the sealEngine used in the generated test fixtures.
    """
    return "NoProof"


@pytest.fixture(autouse=True, scope="session")
def filler_path(request):
    """
    Returns the directory containing the tests to execute.
    """
    return request.config.getoption("filler_path")


@pytest.fixture(autouse=True)
def eips():
    """
    A fixture specifying that, by default, no EIPs should be activated for
    tests.

    This fixture (function) may be redefined in test filler modules in order
    to overwrite this default and return a list of integers specifying which
    EIPs should be activated for the tests in scope.
    """
    return []


@pytest.fixture
def yul(fork: Fork, request):
    """
    A fixture that allows contract code to be defined with Yul code.

    This fixture defines a class that wraps the ::ethereum_test_tools.Yul
    class so that upon instantiation within the test case, it provides the
    test case's current fork parameter. The forks is then available for use
    in solc's arguments for the Yul code compilation.

    Test cases can override the default value by specifying a fixed version
    with the @pytest.mark.compile_yul_with(FORK) marker.
    """
    marker = request.node.get_closest_marker("compile_yul_with")
    if marker:
        if not marker.args[0]:
            pytest.fail(
                f"{request.node.name}: Expected one argument in 'compile_yul_with' marker."
            )
        fork = request.config.fork_map[marker.args[0]]

    class YulWrapper(Yul):
        def __init__(self, *args, **kwargs):
            super(YulWrapper, self).__init__(*args, **kwargs, fork=fork)

    return YulWrapper


SPEC_TYPES: List[Type[BaseTest]] = [StateTest, BlockchainTest]
SPEC_TYPES_PARAMETERS: List[str] = [s.pytest_parameter_name() for s in SPEC_TYPES]


@pytest.fixture(scope="function")
def state_test(
    request, t8n, fork, engine, reference_spec, eips, fixture_collector, base_test_config
) -> StateTestFiller:
    """
    Fixture used to instantiate an auto-fillable StateTest object from within
    a test function.

    Every test that defines a StateTest filler must explicitly specify this
    fixture in its function arguments and set the StateTestWrapper's spec
    property.

    Implementation detail: It must be scoped on test function level to avoid
    leakage between tests.
    """

    class StateTestWrapper(StateTest):
        def __init__(self, *args, **kwargs):
            kwargs["base_test_config"] = base_test_config
            if t8n_dump_dir := request.config.getoption("t8n_dump_dir"):
                kwargs["t8n_dump_dir"] = os.path.join(
                    t8n_dump_dir, convert_test_name_to_path(request.node.name)
                )
            super(StateTestWrapper, self).__init__(*args, **kwargs)
            fixture_collector.add_fixture(
                request.node,
                fill_test(
                    t8n,
                    self,
                    fork,
                    engine,
                    reference_spec,
                    eips=eips,
                ),
            )

    return StateTestWrapper


@pytest.fixture(scope="function")
def blockchain_test(
    request, t8n, fork, engine, reference_spec, eips, fixture_collector, base_test_config
) -> BlockchainTestFiller:
    """
    Fixture used to define an auto-fillable BlockchainTest analogous to the
    state_test fixture for StateTests.
    See the state_test fixture docstring for details.
    """

    class BlockchainTestWrapper(BlockchainTest):
        def __init__(self, *args, **kwargs):
            kwargs["base_test_config"] = base_test_config
            if t8n_dump_dir := request.config.getoption("t8n_dump_dir"):
                kwargs["t8n_dump_dir"] = os.path.join(
                    t8n_dump_dir, convert_test_name_to_path(request.node.name)
                )
            super(BlockchainTestWrapper, self).__init__(*args, **kwargs)
            fixture_collector.add_fixture(
                request.node,
                fill_test(
                    t8n,
                    self,
                    fork,
                    engine,
                    reference_spec,
                    eips=eips,
                ),
            )

    return BlockchainTestWrapper


def pytest_collection_modifyitems(items, config):
    """
    A pytest hook called during collection, after all items have been
    collected.

    Here we dynamically apply "state_test" or "blockchain_test" markers
    to a test if the test function uses the corresponding fixture.
    """
    for item in items:
        if isinstance(item, EIPSpecTestItem):
            continue
        if "state_test" in item.fixturenames:
            marker = pytest.mark.state_test()
            item.add_marker(marker)
        elif "blockchain_test" in item.fixturenames:
            marker = pytest.mark.blockchain_test()
            item.add_marker(marker)
        if "yul" in item.fixturenames:
            marker = pytest.mark.yul_test()
            item.add_marker(marker)


def pytest_make_parametrize_id(config, val, argname):
    """
    Pytest hook called when generating test ids. We use this to generate
    more readable test ids for the generated tests.
    """
    return f"{argname}={val}"


def pytest_runtest_call(item):
    """
    Pytest hook called in the context of test execution.
    """
    if isinstance(item, EIPSpecTestItem):
        return

    class InvalidFiller(Exception):
        def __init__(self, message):
            super().__init__(message)

    if "state_test" in item.fixturenames and "blockchain_test" in item.fixturenames:
        raise InvalidFiller(
            "A filler should only implement either a state test or " "a blockchain test; not both."
        )

    # Check that the test defines either test type as parameter.
    if not any([i for i in item.funcargs if i in SPEC_TYPES_PARAMETERS]):
        pytest.fail(
            "Test must define either one of the following parameters to "
            + "properly generate a test: "
            + ", ".join(SPEC_TYPES_PARAMETERS)
        )
