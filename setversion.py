#!/usr/bin/env python

import sys
import re
from datetime import date

def readme_rewriter(line, versionnum, ctxt):
    expr = ctxt.get("readme_expr", None)
    if not expr:
        expr = re.compile(r"^\*\*Latest Version:")
        ctxt["readme_expr"] = expr
    if expr.match(line):
        return "**Latest Version: {0}**\n".format(versionnum)
    return None


def changelog_rewriter(line, versionnum, ctxt):
    expr = ctxt.get("changelog_expr", None)
    if not expr:
        expr = re.compile(r"^\.\. top-of-changelog")
        ctxt["changelog_expr"] = expr
    if expr.match(line):
        datestr = date.today().strftime("%B %d, %Y")
        cl1 = "CbAPI {0} - Released {1}".format(versionnum, datestr)
        cl2 = "".ljust(len(cl1), "-")
        updates = "\n\nUpdates\n\n.. (add your updates here)\n"
        return line + "\n" + cl1 + "\n" + cl2 + updates
    return None


def doc_conf_rewriter(line, versionnum, ctxt):
    vexpr = ctxt.get("doc_version_expr", None)
    if not vexpr:
        vexpr = re.compile(r"^version = ")
        ctxt["doc_version_expr"] = vexpr
    rexpr = ctxt.get("doc_release_expr", None)
    if not rexpr:
        rexpr = re.compile(r"^release = ")
        ctxt["doc_release_expr"] = rexpr
    if vexpr.match(line):
        t = re.match(r"^(\d+\.\d+)\.", versionnum)
        vn = versionnum
        if t:
            vn = t.group(1)
        return "version = u'{0}'\n".format(vn)
    if rexpr.match(line):
        return "release = u'{0}'\n".format(versionnum)
    return None


def setup_rewriter(line, versionnum, ctxt):
    expr = ctxt.get("setup_expr", None)
    if not expr:
        expr = re.compile(r"^(\s*)version=")
        ctxt["setup_expr"] = expr
    m = expr.match(line)
    if m:
        return "{0}version='{1}'\n".format(m.group(1), versionnum)
    return None


def init_rewriter(line, versionnum, ctxt):
    expr = ctxt.get("init_expr", None)
    if not expr:
        expr = re.compile(r"^__version__ = ")
        ctxt["init_expr"] = expr
    if expr.match(line):
        return "__version__ = '{0}'\n".format(versionnum)
    return None
    

def rewrite_file(infilename, rewritefunc, versionnum, ctxt):
    outfilename = infilename + ".new"
    infile = open(infilename, "r")
    outfile = open(outfilename, "w")
    try:
        s = infile.readline()
        while s:
            s2 = rewritefunc(s, versionnum, ctxt)
            if s2:
                outfile.write(s2)
            else:
                outfile.write(s)
            s = infile.readline()
    finally:
        infile.close()
        outfile.close()
    
def main():
    if len(sys.argv) < 2:
        print("Error: new version number not specified")
        return 1
    version = sys.argv[1]
    ctxt = {}
    rewrite_file("README.md", readme_rewriter, version, ctxt)
    rewrite_file("docs/changelog.rst", changelog_rewriter, version, ctxt)
    rewrite_file("docs/conf.py", doc_conf_rewriter, version, ctxt)
    rewrite_file("setup.py", setup_rewriter, version, ctxt)
    rewrite_file("src/cbapi/__init__.py", init_rewriter, version, ctxt)
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
