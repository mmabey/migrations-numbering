# `migrations-numbering`

A hook for [pre-commit](https://pre-commit.com/) that checks for mis-numbered migration files.

## Installation

```
pip install migrations-numbering
```

Then add an entry to your `.pre-commit-config.yaml` something like this:

```yaml
- repo: https://github.com/mmabey/migrations-numbering
  rev: 0.1.0a1
  hooks:
  - id: migrations-numbering
    files: \d+_.*.up.sql$
```

Take a look at the [pre-commit](https://pre-commit.com/) documentation for more information on installation.


## Configuration

Configuration of the hook can be done by environment variables, command-line parameters, or by configuring pre-commit.
The two configurations are:

1. The name of the directory that stores the migration files. Defaults to "migrations".
2. The regular expression used to identify files that are migration files. Default is `^(\d+)(_.*)$`, which will match
   all files that have a number followed by an underscore anywhere in the filename.

The two respective environment variables are:

1. `PRE_COMMIT_MIGRATION_NUMBERING_DEFAULT_DIRNAME`
2. `PRE_COMMIT_MIGRATION_NUMBERING_DEFAULT_REGEX`

The corresponding command-line parameters (only useful if running the tool manually) are:

1. `--dirname`
2. `--regex`

To change these values via the pre-commit config, change the `repo` entry to something like this:

```yaml
- repo: https://github.com/mmabey/migrations-numbering
  rev: 0.1.0a1
  hooks:
  - id: migrations-numbering
    args: [--dirname=migration, --regex="\d+_.*.up.sql$"]
```

Note: Setting the `files` configuration to match your migration files is more efficient than adding an equivalent
pattern to the `--regex` argument.
