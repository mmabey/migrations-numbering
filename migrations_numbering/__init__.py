#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime, timezone
from pathlib import Path
from typing import AnyStr, List, Optional

import click

__version__ = "0.1.0a2"

DEFAULT_DIRNAME = os.getenv(
    "PRE_COMMIT_MIGRATION_NUMBERING_DEFAULT_DIRNAME", "migrations"
)
DEFAULT_REGEX = os.getenv(
    "PRE_COMMIT_MIGRATION_NUMBERING_DEFAULT_REGEX", r"^(\d+)(_.*)$"
)

file_info = namedtuple("file_info", ("file", "num", "name", "date"))
sys_print = print


@click.command()
@click.argument("files", nargs=-1, type=click.Path(resolve_path=True))
@click.option("--dirname", default=DEFAULT_DIRNAME)
@click.option("--regex", default=DEFAULT_REGEX)
@click.option("-v", "--verbose", default=False, is_flag=True)
def main(files: List[click.Path], dirname: AnyStr, regex: AnyStr, verbose: bool) -> int:
    pat = re.compile(regex)

    def print(*args, **kwargs):
        if verbose:
            sys_print(*args, **kwargs)

    def new_fi(
        path_obj: Path, mig_num: Optional[int] = None, mig_name: Optional[str] = None
    ) -> file_info:
        """Create a new file_info object from the given Path object."""
        if None in {mig_num, mig_name}:
            _m = re.match(pat, path_obj.name)
            if _m:
                mig_num = int(_m.group(1))
                mig_name = _m.group(2)
        proc_result = subprocess.run(
            args=f"git log --format=%ad --date=iso -- {path_obj.name} | tail -1",
            shell=True,
            cwd=str(path_obj.parent.resolve()),
            stdout=subprocess.PIPE,
        )
        default_date = datetime(9999, 12, 31, tzinfo=timezone.utc)
        try:
            proc_result.check_returncode()
            date_added = datetime.strptime(
                proc_result.stdout.decode("utf-8").strip(), "%Y-%m-%d %H:%M:%S %z"
            )
        except (subprocess.CalledProcessError, ValueError):
            # Just use an arbitrarily high date for comparison
            date_added = default_date
        print(f"       {date_added}")
        return file_info(file=path_obj, num=mig_num, name=mig_name, date=date_added)

    maybe_rename = defaultdict(list)
    maybe_rename_files = set()

    for f in files:
        f = Path(str(f))
        print(f"File passed from pre-commit: {str(f)}")
        m = re.match(pat, f.name)
        if dirname in f.parts and m and f.resolve().exists():
            # At this point we know f is a changed migration file
            maybe_rename[f.parent].append(new_fi(f, int(m.group(1)), m.group(2)))
            maybe_rename_files.add(f)

    files_have_changed = False
    for mig_dir in maybe_rename:
        print(f"Renaming {len(maybe_rename[mig_dir])} migration files in {mig_dir}")

        assert isinstance(mig_dir, Path)
        # Create a sorted set of files in the migration directory minus the ones we
        # might need to rename.
        existing_files = set(f for f in mig_dir.glob("*") if f.resolve().exists())
        existing_files = list(existing_files - maybe_rename_files)
        existing_files.sort(key=lambda x: int(re.match(pat, x.name).group(1)))

        # Get the highest numbered migration file that isn't a staged change
        max_mig_num = -1
        found_existing_problem = False
        print("\nHere's the list of existing files:")
        for f in existing_files:
            print(str(f))
        print()
        for f in existing_files:
            if found_existing_problem:
                # If this happens, all remaining files from the glob need to be added
                # to the set of files to be renamed.
                print(f"Adding {f.name} to list of files to rename")
                maybe_rename[mig_dir].append(new_fi(f))
                continue

            m = re.match(pat, f.name)
            if m:
                this_num = int(m.group(1))
                if this_num == (max_mig_num + 1):
                    print(f"Setting max_mig_num to {m.group(1)}")
                    max_mig_num = int(m.group(1))
                else:
                    # This means there already existed a duplicate migration number or
                    # that a number was skipped
                    print(
                        f"Found a problem with existing migrations.\n  max: {max_mig_num}\n  this: {this_num}"
                    )
                    print(f"Adding {f.name} to list of files to rename")
                    maybe_rename[mig_dir].append(new_fi(f))
                    found_existing_problem = True
                    continue

        print(f"\nMax number is currently: {max_mig_num}")

        maybe_rename[mig_dir].sort(key=lambda x: f"{x.num:010}|{x.date.isoformat()}")
        print(f"Sorted entries from {mig_dir}:")
        for m in maybe_rename[mig_dir]:
            print(f"{m.num} - {m.file.name}")

        for f_info in maybe_rename[mig_dir]:
            max_mig_num += 1
            new_name = f"{max_mig_num}{f_info.name}"
            if f_info.file.name == new_name:
                print(f"Skipped renaming {f_info.file.name}")
                continue
            try:
                f_info.file.rename(mig_dir / new_name)
                print(f"Renamed {f_info.file.name}\n" f"     to {new_name}\n")
            except FileNotFoundError:
                # It's possible for pre-commit to pass the same file to this function
                # more than once, causing this exception if we've already renamed the
                # current file we're working with (f_info).
                continue
            files_have_changed = True

    return int(files_have_changed)


if __name__ == "__main__":
    exit(main())
