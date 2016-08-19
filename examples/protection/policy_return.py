from cbapi.protection import CbEnterpriseProtectionAPI
from cbapi.protection.models import Computer

p = CbEnterpriseProtectionAPI()

for computer in p.select(Computer).where("policyId:5"):
    print("%s was in %s" % (computer.name, computer.policyName))
    computer.policyId = computer.previousPolicyId
    computer.save()
    print ("%s is now in %s" % (computer.name, "is now in", computer.policyName))
