from cbapi.defense import *
import unittest
import sys
import os
import glob
import time
import json

sys.path.append(os.path.dirname(__file__))
import requests_cache


def test_policy(rulefiles):
    requests_cache.uninstall_cache()
    defense_api = CbDefenseAPI(profile="test")


    default_policies = [policy for policy in defense_api.select(Policy) if policy.name == "default"]
    new_policy = defense_api.create(Policy)
    new_policy.policy = default_policies[0].policy
    new_policy.name = "cbapi-python-test-%d" % time.time()
    new_policy.priorityLevel = "LOW"
    new_policy.description = "Test policy"
    new_policy.version = 2
    new_policy.save()

    for t in rulefiles:
        try:
            test_rule(new_policy, t)
            print("Added rule %s" % t)
        except Exception as e:
            print("Exception adding rule %s: %s" % (t, e))

    new_policy.delete()


def test_rule(new_policy, fn):
    new_rule = json.load(open(fn, "r"))
    new_policy.add_rule(new_rule)


if __name__ == '__main__':
    rulefiles = glob.glob(os.path.join(os.path.dirname(__file__), "data", "defense", "policy_rules", "*.json"))
    print(rulefiles)

    test_policy(rulefiles)


    unittest.main()
