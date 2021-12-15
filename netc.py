from decouple import config
from ncclient import manager
import pdb


USER=config('NET_USER')
PASS=config('PASS')
HOST=config('TEST_HOST')


eos = manager.connect(host=HOST, port='830', 
        timeout=30, username=USER, password=PASS, hostkey_verify=False)

cell = ''' 
    <cellwan-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-cellwan-oper">
      <cellwan-radio>
        <cellular-interface>Cellular0/1/0</cellular-interface>
        <radio-power-mode>radio-power-mode-online</radio-power-mode>
      </cellwan-radio>
    </cellwan-oper-data>
'''

output=eos.get(filter=("subtree", cell))
print(output)



eos.close_session()

