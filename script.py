


#! /usr/bin/env python
import lxml.etree as et
from argparse import ArgumentParser
from ncclient import manager
from ncclient.operations import RPCError

from decouple import config

USER=config('NET_USER')
PASS=config('PASS')
HOST=config('TEST_HOST')

payload = [
'''
<get xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <filter>
    <cellwan-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-cellwan-oper">
      <cellwan-radio>
        <cellular-interface>Cellular0/1/0</cellular-interface>
        <radio-power-mode>radio-power-mode-online</radio-power-mode>
      </cellwan-radio>
    </cellwan-oper-data>
  </filter>
</get>
''',
]

if __name__ == '__main__':

    parser = ArgumentParser(description='Usage:')


    # connect to netconf agent
    with manager.connect(host=HOST,
                         port='830',
                         username=USER,
                         password=PASS,
                         timeout=90,
                         hostkey_verify=False,
                         device_params={'name': 'csr'}) as m:

        # execute netconf operation
        for rpc in payload:
            try:
                response = m.dispatch(et.fromstring(rpc))
                import pdb
                pdb.set_trace()
                data = response.data_ele
            except RPCError as e:
                data = e._raw
            except:
                print(response)

            # beautify output
            print(et.tostring(data, encoding='unicode', pretty_print=True))

