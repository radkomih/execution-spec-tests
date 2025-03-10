# Quick Start

!!! info "Testing features under active development"
    The EVM features under test must be implemented in the `evm` tool and `solc` executables that are used by the execution-spec-tests framework. The following guide installs stable versions of these tools.

    To test features under active development, start with this base configuration and then follow the steps in [executing tests for features under development](./executing_tests_dev_fork.md). 

The following requires a Python 3.10, 3.11 or 3.12 installation.

1. Ensure `go-ethereum`'s `evm` tool and `solc` ([0.8.20](https://github.com/ethereum/solidity/releases/tag/v0.8.20) or [0.8.21](https://github.com/ethereum/solidity/releases/tag/v0.8.21)) are in your path. Either build the required versions, or alternatively:

    === "Ubuntu"

          ```console
          sudo add-apt-repository -y ppa:ethereum/ethereum
          sudo apt-get update
          sudo apt-get install ethereum solc
          ```
          More help:

          - [geth installation doc](https://geth.ethereum.org/docs/getting-started/installing-geth#ubuntu-via-ppas).
          - [solc installation doc](https://docs.soliditylang.org/en/latest/installing-solidity.html#linux-packages).

    === "macOS"

          ```console
          brew update
          brew upgrade
          brew tap ethereum/ethereum
          brew install ethereum solidity
          ```
          More help:

          - [geth installation doc](https://geth.ethereum.org/docs/getting-started/installing-geth#macos-via-homebrew).
          - [solc installation doc](https://docs.soliditylang.org/en/latest/installing-solidity.html#macos-packages).

    === "Windows"

          Binaries available here:

          - [geth](https://geth.ethereum.org/downloads) (binary or installer).
          - [solc](https://github.com/ethereum/solidity/releases).

          More help:

          - [geth installation doc](https://geth.ethereum.org/docs/getting-started/installing-geth#windows).
          - [solc static binaries doc](https://docs.soliditylang.org/en/latest/installing-solidity.html#static-binaries).

2. Clone the [execution-spec-tests](https://github.com/ethereum/execution-spec-tests) repo and install its dependencies (it's recommended to use a virtual environment for the installation):

    ```console
    git clone https://github.com/ethereum/execution-spec-tests
    cd execution-spec-tests
    python3 -m venv ./venv/
    source ./venv/bin/activate
    pip install -e '.[docs,lint,test]'
    ```

3. Verify installation:
    1. Explore test cases:

        ```console
        fill --collect-only
        ```

        Expected console output:
        <figure markdown>  <!-- markdownlint-disable MD033 (MD033=no-inline-html) -->
            ![Screenshot of pytest test collection console output](./img/pytest_collect_only.png){align=center}
        </figure>

    2. Execute the test cases (verbosely) in the `./tests/berlin/eip2930_access_list/test_acl.py` module:

        ```console
        fill -v tests/berlin/eip2930_access_list/test_acl.py
        ```

        Expected console output:
        <figure markdown>  <!-- markdownlint-disable MD033 (MD033=no-inline-html) -->
            ![Screenshot of pytest test collection console output](./img/pytest_run_example.png){align=center}
        </figure>
        Check:

        1. The versions of the `evm` and `solc` tools are as expected (your versions may differ from those in the highlighted box).
        2. The corresponding fixture file has been generated:

            ```console
            head fixtures/berlin/eip2930_access_list/acl/access_list.json
            ```

## Next Steps

1. Learn [useful command-line flags](./executing_tests_command_line.md).
2. [Execute tests for features under development](./executing_tests_dev_fork.md) via the `--fork` flag.
3. _Optional:_ [Configure VS Code](./setup_vs_code.md) to auto-format Python code and [execute tests within VS Code](./executing_tests_vs_code.md#executing-and-debugging-test-cases).
4. Implement a new test case, see [Writing Tests](../writing_tests/index.md).
