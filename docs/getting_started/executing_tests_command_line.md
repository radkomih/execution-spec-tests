# Executing Tests at a Prompt

The execution-spec-tests test framework uses the [pytest framework](https://docs.pytest.org/en/latest/) for test case collection and execution. The `fill` command is essentially an alias for `pytest`, which uses several [custom pytest plugins](../library/pytest_plugins/index.md) to run transition tools against test cases and generate JSON fixtures.

!!! note "Options specific to execution-spec-tests"
    The command-line options specific to filling tests can be listed via:

    ```console
    fill --test-help
    ```

    See [Custom `fill` Command-Line Options](#custom-fill-command-line-options) for all options.

## Collection - Test Exploration

The test cases implemented in the `./tests` sub-directory can be listed in the console using:

```console
fill --collect-only
```

and can be filtered (by test path, function and parameter substring):

```console
fill --collect-only -k warm_coinbase
```

Docstrings are additionally displayed when ran verbosely:

```console
fill --collect-only -k warm_coinbase -vv
```

## Execution

By default, test cases are executed for all forks already deployed to mainnet, but not for forks still under active development, i.e., as of time of writing, Q2 2023:

```console
fill
```

will generate fixtures for test cases from Frontier to Shanghai.

To generate all the test fixtures defined in the `./tests/shanghai` sub-directory and write them to the `./fixtures-shanghai` directory, run `fill` in the top-level directory as:

```console
fill ./tests/shanghai --output="fixtures-shanghai"
```

!!! note "Test case verification"
    Note, that the (limited set of) test `post` conditions are tested against the output of the `evm t8n` command during test generation.

To generate all the test fixtures in the `tests/shanghai/eip3651_warm_coinbase/test_warm_coinbase.py` module, for example, run:

```console
fill tests/shanghai/eip3651_warm_coinbase/test_warm_coinbase.py
```

To generate specific test fixtures from a specific test function or even test function and parameter set, obtain the corresponding test ID using:

```console
fill --collect-only -q -k test_warm_coinbase
```

This filters the tests by `test_warm_coinbase`. Then find the relevant test ID in the console output and provide it to fill, for example, for a test function:

```console
fill tests/shanghai/eip3651_warm_coinbase/test_warm_coinbase.py::test_warm_coinbase_gas_usage
```

or, for a test function and specific parameter combination:

```console
fill tests/shanghai/eip3651_warm_coinbase/test_warm_coinbase.py::test_warm_coinbase_gas_usage[fork=Merge-DELEGATECALL]
```

## Execution for Development Forks

!!! note ""
    By default, test cases are not executed with upcoming Ethereum forks so that they can be readily executed against the `evm` tool from the latest `geth` release.

    In order to execute test cases for an upcoming fork, ensure that the `evm` tool used supports that fork and features under test and use the `--until` or `--fork` flag.
    
    For example, as of Q2 2023, the current fork under active development is `Cancun`:
    ```console
    fill --until Cancun
    ```

    See: [Executing Tests for Features under Development](./executing_tests_dev_fork.md).

## Debugging the `t8n` Command

The `--t8n-dump-dir` flag can be used to dump the inputs and outputs of every call made to the `t8n` command for debugging purposes, see [Debugging Transition Tools](./debugging_t8n_tools.md).

## Other Useful Pytest Command-Line Options

```console
fill -vv            # More verbose output
fill -x             # Exit instantly on first error or failed test case
fill --pdb          # Drop into the debugger upon error in a test case
```

## Custom `fill` Command-Line Options

Options added by the execution-spec-tests pytest plugins can be listed with:

```console
fill --test-help
```

Output:

```console
usage: fill [-h] [--evm-bin EVM_BIN] [--traces] [--solc-bin SOLC_BIN]
            [--filler-path FILLER_PATH] [--output OUTPUT] [--flat-output]
            [--enable-hive] [--forks] [--fork FORK] [--from FROM]
            [--until UNTIL] [--test-help]

options:
  -h, --help            show this help message and exit

Arguments defining evm executable behavior:
  --evm-bin EVM_BIN     Path to an evm executable that provides `t8n`. Default:
                        First 'evm' entry in PATH.
  --traces              Collect traces of the execution information from the
                        transition tool.

Arguments defining the solc executable:
  --solc-bin SOLC_BIN   Path to a solc executable (for Yul source compilation).
                        Default: First 'solc' entry in PATH.

Arguments defining filler location and output:
  --filler-path FILLER_PATH
                        Path to filler directives
  --output OUTPUT       Directory to store the generated test fixtures. Can be
                        deleted.
  --flat-output         Output each test case in the directory without the
                        folder structure.
  --enable-hive         Output test fixtures with the hive-specific properties.

Arguments defining debug behavior:
  --t8n-dump-dir T8N_DUMP_DIR
                        Path to dump the transition tool debug output.

Specify the fork range to generate fixtures for:
  --forks               Display forks supported by the test framework and exit.
  --fork FORK           Only fill tests for the specified fork.
  --from FROM           Fill tests from and including the specified fork.
  --until UNTIL         Fill tests until and including the specified fork.

Arguments related to running execution-spec-tests:
  --test-help           Only show help options specific to execution-spec-tests
                        and exit.

Exit: After displaying help.
```
