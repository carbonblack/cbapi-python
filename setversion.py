#!/usr/bin/env python

import sys
import re

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
        pass
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
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
