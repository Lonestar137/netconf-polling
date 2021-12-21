from decouple import config
from ncclient import manager
import xml.etree.ElementTree as ET
import scheduling


USER=config('NET_USER')
PASS=config('PASS')
HOST=config('TEST_HOST2')


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

root = ET.fromstring(str(output))


#Define variables to retrieve here:
for i in root[0][0][0].getchildren(): print(str(i.tag.split('}')[1] + ':  '+ i.text)+'\n')



eos.close_session()

