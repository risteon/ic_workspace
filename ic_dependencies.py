#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Christoph Rist"
__copyright__ = "Copyright 2017, risteon"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Christoph Rist"
__email__ = "rist.christoph@gmail.com"

import sys
from os import path, listdir, makedirs, getcwd
import argparse
import json
# pip: gitpython
try:
    from git import Repo
except ImportError:
    print("gitpython is not available. Try installing it with '$ pip3 install gitpython'", file=sys.stderr)
    exit(1)


PACKAGES_FILE = 'ic_packages_info.json'
DEPS_FILE = 'ic_dependencies.json'


class Workspace:
    def __init__(self):
        self._root = None
        self._package_path = None
        self.packages = {}
        self.package_db = {}
        self._missing = []
        self._unknown = []
        self._include_order = []
        self._circular = None

    def init(self, ic_folder):
        self._root = ic_folder
        self._package_path = path.join(ic_folder, 'packages')
        self.packages = {}
        self.package_db = {}
        self._missing = set()
        self._unknown = set()
        self._include_order = []
        try:
            self.package_db = self._read_packages_dict()
        except FileNotFoundError:
            print("Warning: Packages file {} missing in workspace directory {}."
                  .format(PACKAGES_FILE, ic_folder), file=sys.stderr)
        self.scan()
        try:
            self._include_order = self._build_graph()
            self._circular = False
        except RuntimeError:
            self._circular = True
            print("Circular dependency.", file=sys.stderr)

    def _read_packages_dict(self):
        with open(path.join(self._root, PACKAGES_FILE), 'r') as f:
            return json.load(f)

    def _read_package_deps(self, package):
        f_path = path.join(self._package_path, package, DEPS_FILE)
        if not path.isfile(f_path):
            # warning level
            print("Warning: Dependencies file for package '{}' does not exist.".format(package))
            return []

        with open(f_path, 'r') as f:
            return set(json.load(f))

    def write_cmakelists(self):
        if self._circular:
            return
        with open(path.join(self._package_path, 'CMakeLists.txt'), 'w') as cml:
            for p in self._include_order:
                cml.write("ADD_SUBDIRECTORY({})\n".format(p))

    def scan(self):
        if not path.exists(self._package_path):
            makedirs(self._package_path)

        dirs = [d for d in listdir(self._package_path) if path.isdir(path.join(self._package_path, d))]
        self._update_deps_for(dirs)

    def _update_deps_for(self, packages):
        for p in packages:
            self.packages[p] = self._read_package_deps(p)

        for p in self.packages:
            for d in self.packages[p]:
                if d not in self.packages:
                    self._missing.add(d)

        rm = set()   # < move from missing to unknown
        for m in self._missing:
            if m not in self.package_db:
                self._unknown.add(m)
                rm.add(m)

        for m in rm:
            self._missing.remove(m)

    def _clone_packages(self, packages):
        cloned = set()
        for p in packages:
            if p not in self.package_db:
                print("Warning: Package '{}' not found in {}. Skipping.".format(p, PACKAGES_FILE), file=sys.stderr)
                continue
            dest = path.join(self._package_path, p)
            if path.exists(dest):
                print("\t-> {} already exists.".format(p))
            else:
                print("\t-> Cloning {}...".format(p), end="")
                sys.stdout.flush()
                Repo.clone_from(self.package_db[p], dest)
                print(" OK")
                cloned.add(p)
            self._missing.discard(p)
        return cloned

    def _build_graph(self):
        order = []
        g = self.packages.copy()

        def rm(dep):
            for package in g:
                g[package].discard(dep)

        # remove unknowns
        for u in self._unknown:
            rm(u)

        while g:
            for p in g:
                if not g[p]:
                    order.append(p)
                    del g[p]
                    rm(p)
                    break
            else:
                raise RuntimeError("Circular dependency")

        return order

    def add_packages(self, packages):
        for p in packages:
            self._missing.add(p)
        while self._missing:
            tmp = list(self._missing)
            cloned = self._clone_packages(tmp)
            self._update_deps_for(cloned)
        # update deps graph
        try:
            self._include_order = self._build_graph()
            self._circular = False
        except RuntimeError:
            self._circular = True
            print("Circular dependency.", file=sys.stderr)

    def print_status(self):
        print("Existing packages:")
        for p in self.packages:
            print("\t{}".format(p))
        print("Dependencies to checkout:")
        for p in self._missing:
            print("\t{}".format(p))
        if self._unknown:
            print("The following dependency packages are unknown:")
            for m in self._unknown:
                print("\t{}".format(m))


def main():
    # arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--ic_folder", type=str,
                        help="icl_workspace directory", dest='ic_folder')

    # TODO
    parser.add_argument("-i", "--ignore-missing", action='store_true')
    parser.add_argument("-u", "--update", action='store_true')
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("-c", "--check", action='store_true')

    parser.add_argument("-a", "--add", type=str, nargs='*', dest='add')
    args = parser.parse_args()

    if args.ic_folder:
        ic_folder = args.ic_folder
    else:
        ic_folder = getcwd()

    mode = 'status'
    packages = None
    if args.add:
        mode = 'add'
        packages = args.add
    elif args.check:
        mode = 'check'

    ws = Workspace()
    ws.init(ic_folder)

    if mode == 'add':
        ws.add_packages(packages)
        ws.write_cmakelists()
    elif mode == 'check':
        ws.add_packages([])
        ws.write_cmakelists()

    if args.verbose:
        ws.print_status()


if __name__ == "__main__":
    main()
