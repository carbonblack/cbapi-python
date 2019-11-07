#!/usr/bin/env python

import sys
import os
import re
import argparse
from datetime import date

def readme_rewriter(line, ctxt):
    expr = ctxt.get("readme_expr", None)
    if not expr:
        expr = re.compile(r"^\*\*Latest Version:")
        ctxt["readme_expr"] = expr
    if expr.match(line):
        return "**Latest Version: {0}**\n".format(ctxt["version"])
    return None


def changelog_rewriter(line, ctxt):
    expr = ctxt.get("changelog_expr", None)
    if not expr:
        expr = re.compile(r"^\.\. top-of-changelog")
        ctxt["changelog_expr"] = expr
    if expr.match(line):
        datestr = date.today().strftime("%B %d, %Y")
        cl1 = "CbAPI {0} - Released {1}".format(ctxt["version"], datestr)
        cl2 = "".ljust(len(cl1), "-")
        updates = "\n\nUpdates\n\n.. (add your updates here)\n"
        return line + "\n" + cl1 + "\n" + cl2 + updates
    return None


def doc_conf_rewriter(line, ctxt):
    vexpr = ctxt.get("doc_version_expr", None)
    if not vexpr:
        vexpr = re.compile(r"^version = ")
        ctxt["doc_version_expr"] = vexpr
    rexpr = ctxt.get("doc_release_expr", None)
    if not rexpr:
        rexpr = re.compile(r"^release = ")
        ctxt["doc_release_expr"] = rexpr
    if vexpr.match(line):
        t = re.match(r"^(\d+\.\d+)\.", ctxt["version"])
        vn = ctxt["version"]
        if t:
            vn = t.group(1)
        return "version = u'{0}'\n".format(vn)
    if rexpr.match(line):
        return "release = u'{0}'\n".format(ctxt["version"])
    return None


def setup_rewriter(line, ctxt):
    expr = ctxt.get("setup_expr", None)
    if not expr:
        expr = re.compile(r"^(\s*)version=")
        ctxt["setup_expr"] = expr
    m = expr.match(line)
    if m:
        return "{0}version='{1}'\n".format(m.group(1), ctxt["version"])
    return None


def init_rewriter(line, ctxt):
    expr = ctxt.get("init_expr", None)
    if not expr:
        expr = re.compile(r"^__version__ = ")
        ctxt["init_expr"] = expr
    if expr.match(line):
        return "__version__ = '{0}'\n".format(ctxt["version"])
    return None
    

def rewrite_file(infilename, rewritefunc, ctxt):
    outfilename = infilename + ".new"
    infile = open(infilename, "r")
    outfile = open(outfilename, "w")
    try:
        s = infile.readline()
        while s:
            s2 = rewritefunc(s, ctxt)
            if s2:
                outfile.write(s2)
            else:
                outfile.write(s)
            s = infile.readline()
    finally:
        infile.close()
        outfile.close()
    if not ctxt.get("nodelete", False):
        os.remove(infilename)
        os.rename(outfilename, infilename)
    
    
def main():
    parser = argparse.ArgumentParser(description="Set the version number in CbAPI source and documentation")
    parser.add_argument("version", help="New version number to add")
    parser.add_argument("-n", "--nodelete", action="store_true", help="Do not delete existing files, leave new files with .new extension")
    
    args = parser.parse_args()
    ctxt = {"version": args.version, "nodelete": args.nodelete}
    rewrite_file("README.md", readme_rewriter, ctxt)
    rewrite_file("docs/changelog.rst", changelog_rewriter, ctxt)
    rewrite_file("docs/conf.py", doc_conf_rewriter, ctxt)
    rewrite_file("setup.py", setup_rewriter, ctxt)
    rewrite_file("src/cbapi/__init__.py", init_rewriter, ctxt)
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
