import sys
import sqlite3
import requests_cache
import os
import pprint


def compare_json(gold_root, other_root, path, errors):
    if type(gold_root) != type(other_root):
        errors.append("%s: type mismatch. expected type(%s), got type(%s)" % (path, type(gold_root).__name__,
                                                                              type(other_root).__name__))

    if type(gold_root) == dict:
        for key in gold_root.keys():
            newpath = "%s.%s" % (path, key)
            if key not in other_root:
                errors.append("%s: not found. should have value %s" % (newpath, gold_root[key]))
            else:
                compare_json(gold_root[key], other_root[key], newpath, errors)

        for key in other_root.keys():
            newpath = "%s.%s" % (path, key)
            if key not in gold_root:
                errors.append("%s: now has value %s in the new output" % (newpath, other_root[key]))
    """
    elif type(gold_root) == list:
        if len(gold_root) != len(other_root):
            errors.append("%s: length mismatch. expected %d, got %d" % (path, len(gold_root), len(other_root)))
            return
        for i in range(len(gold_root)):
            newpath = "%s[%d]" % (path, i)
            compare_json(gold_root[i], other_root[i], newpath, errors)
    """
    #else:
    #    if gold_root != other_root:
    #        errors.append("%s: (%s) expected %s, got %s" % (path, type(gold_root).__name__, gold_root, other_root))


def main(argv):
    if len(sys.argv) != 3:
        print "Usage python compare_responses.py <sqlitedb1> <sqlitedb2>"

    db1 = sys.argv[1]
    db2 = sys.argv[2]

    con1 = sqlite3.connect(db1)
    con2 = sqlite3.connect(db2)

    cur1 = con1.cursor()
    cur2 = con2.cursor()

    cur1.execute("SELECT key FROM responses")
    cur2.execute("SELECT key FROM responses")

    db1_responses = cur1.fetchall()
    db2_responses = cur2.fetchall()

    #
    # Get all responses from db1
    #
    db1_cache = requests_cache.backends.DbCache(location=os.path.splitext(db1)[0])
    db2_cache = requests_cache.backends.DbCache(location=os.path.splitext(db2)[0])

    local_cache = []
    #
    # compare first argument to second
    #
    for db1_response in db1_responses:

        if db1_response in local_cache:
            continue
        else:
            local_cache.append(db1_response)

        if db1_response in db2_responses:
            response1, _ = db1_cache.get_response_and_time(db1_response[0])
            response2, _ = db2_cache.get_response_and_time(db1_response[0])

            errors = []
            path = ""
            try:
                compare_json(response1.json(), response2.json(), path, errors)
            except ValueError:
                print "[-]: Unable to decode as JSON from URL: %s" % db1_response[0]
                print "[-]: Content looks like this: %s" % response1.content
            if errors:
                print "[-]: Error in url: %s" % db1_response[0]
                for error in errors:
                    print error
            else:
                print "[+]: Success URL: %s" % db1_response[0]


    #
    # compare second to first
    #
    for db2_response in db2_responses:

        if db2_response in local_cache:
            continue
        else:
            local_cache.append(db2_response)

        if db2_response in db1_responses:
            response1, _ = db1_cache.get_response_and_time(db2_response[0])
            response2, _ = db2_cache.get_response_and_time(db2_response[0])

            errors = []
            path = ""
            try:
                compare_json(response1.json(), response2.json(), path, errors)
            except ValueError:
                print "[-]: Unable to decode as JSON from URL: %s" % db2_response[0]
                print "[-]: Content looks like this: %s" % response1.content
            if errors:
                print "[-]: Error in url: %s" % db2_response[0]
                pprint.pprint(errors)
            else:
                print "[+]: Success URL: %s" % db2_response[0]

    print len(local_cache)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
