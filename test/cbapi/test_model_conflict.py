import pytest
from cbapi.psc.models import Policy
from cbapi.psc.defense.models import Policy as PolicyOld
from cbapi.example_helpers import get_cb_defense_object

class TempArgs:
    pass

def test_model_conflict():
    # this is setup temporary stuff
    args = TempArgs()
    args.verbose = False
    args.cburl = "https://localhost.example.com"
    args.apitoken = "foo"
    args.no_ssl_verify = True
    apiobj = get_cb_defense_object(args)
    # this is the actual test
    mod1 = Policy(apiobj)
    mod2 = PolicyOld(apiobj)
    mod1.do_funky_things()
    with pytest.raises(AttributeError):
        mod2.do_funky_things()
    