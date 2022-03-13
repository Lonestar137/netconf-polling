from decouple import config
from ncclient import manager

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET
import xmltodict, pprint
import schedule, csv, time, datetime
import json

import psycopg2
import logging

import queue
import threading
from concurrent.futures import ThreadPoolExecutor

#Abstracts away the type of poll protocol used
class protocolProcessor:
    def __init__(self, hosts: dict):
        self.__hosts = hosts


        # Dictionary for storing associated protocol hosts , poll frequency, and template file names
        self.SNMPHosts = {}
        self.netconfHosts = {}

    def getTemplateType(self):
        #TODO Clean up this function

        i = 0
        #Export json
        for host, v in self.__hosts.items():
            for template in v['templates']:
                poll_info = {
                         i: { 
                            'host': host,
                            'template': template,
                            'frequency': v['frequency']
                  }
                }

                if '.netconf' == template[-8:]:
                    #print(template, 'is netconf')
                    self.useNetconf(poll_info)
                elif '.snmp' == template[-5:]:
                    #print(template, 'is snmp')
                    self.useSNMP(poll_info)
                else:
                    print('Invalid template name found: '+ template +'.  Please create or rename your template files, e.g. template.netconf or template.snmp')
                    print('Also, make sure that templates are named correctly in your hosts file.')
                    exit()
                i+=1
        return 1

    def useNetconf(self, info: dict)->dict:
        self.netconfHosts.update(info) 

        return self.netconfHosts
        
    
    def useSNMP(self, info)->dict:
        self.SNMPHosts.update(info) 

        return self.SNMPHosts

    def start_protocol(self):

        if self.SNMPHosts != {}:
            print(self.SNMPHosts)
            self.SNMP = snmp(self.SNMPHosts)
            self.SNMP.schedulePoll()

        if self.netconfHosts != {}:
            self.NETCONF = netconf(self.netconfHosts)
            self.NETCONF.schedulePoll()
                
        # if whatever other protocols you want to implement. Just create the class and call it here.

        print('Starting jobs')
        #Start all scheduled jobs.
        while True:
            schedule.run_pending()




#Basic functions shared for all protocols.
class protocolBase:
    executor = ThreadPoolExecutor(3)
    future = ''

    def getTemplateRPC(self, host, template):
        # Returns True if the template is found in the directory.

        try:
            #Get list of filenames in /templates
            template_files = [f for f in listdir('./templates') if isfile(join('./templates', f))]
        except FileNotFoundError:
            print('Cannot find templates dir.  Make sure it exists in the main project directory.')
            exit()

        if template_files == []:
            print('templates/ is empty.')
            exit()

        if template in template_files:
            with open('./templates/'+template, 'r') as f:
                rpc=f.read()
                assert '' != rpc, print('RPC call string is empty. Check your '+template+' file and make sure it is not empty.')
            return rpc
        else:
            print('No matching template found for '+ template + '.')
            return ''

    def run_scheduled(self):
        # Class method for starting scheduled jobs.
        while True:
            schedule.run_pending()



#Netconf polling code
class netconf(protocolBase):
    def __init__(self, host_dict: dict):
        self.hosts_to_poll = host_dict
        assert dict == type(self.hosts_to_poll), print('Netconf class only takes type dict.')
        assert {} != self.hosts_to_poll, print('Empty dictionary passed to netconf class.')

        self.__USER = config('USER')
        self.__PASS = config('PASS')
        #ex: 
        """
        {
           1: {
            "host": "10.100.1.1", 
                "frequency": 10,
                "template": ""
            }
        }

        """
    def poll(self, host, rpc):
        try:
            #Connect to device
            eos = manager.connect(host=host, port='830', 
                    timeout=10, username=self.__USER, password=self.__PASS, hostkey_verify=False)

            #Get xml root for parsing, i.e (The returned output of the rpc call to device.)
            output=eos.get(filter=("subtree", rpc))
            #root = ET.fromstring(str(output))
            print('-====Connected to '+host+'====-')

            def print_all_KVs(d: dict):
                for k,v in d.items():
                    if type(v) == dict:
                        dfs(v)
                    else:
                        print(k,v)

            #TODO Send dict to databaseHandler.
            rpc_dict = xmltodict.parse(str(output))

            #TODO comment out these two lines. Only useful for logging.
            pprint.pprint(rpc_dict['rpc-reply']['@xmlns'], indent=1) # Shows netconf version, not necess
            pprint.pprint(rpc_dict['rpc-reply']['data'], indent=1)

            # Recursively print out all the keys and values in the dictionary.
            print_all_KVs(rpc_dict['rpc-reply']['data'])

            eos.close_session()

        except Exception as e:
            #TODO LOGGING
            print(str(e)+' for host: '+host)
            return 0



    def schedulePoll(self):

        for index, v in self.hosts_to_poll.items():
            rpc = self.getTemplateRPC(v['host'], v['template'])
            if rpc != '':
                # jobqueue put here
                #schedule.every(v['frequency']).seconds.do(self.poll, v['host'], rpc) #Non async call
                schedule.every(v['frequency']).seconds.do(self.executor.submit, self.poll, v['host'], rpc) #async call

        print('Netconf polls scheduled.')




class snmp(protocolBase):
    #TODO Add snmp specific polling functions here.

    def __init__(self, host_dict):
        self.hosts_to_poll = host_dict

        assert dict == type(self.hosts_to_poll), print('SNMP class only takes type dict.')
        assert {} != self.hosts_to_poll, print('Empty dictionary passed to snmp class.')

    def poll(self, host, rpc):
        pass

    def schedulePoll(self):
        for index, v in self.hosts_to_poll.items():
            rpc = self.getTemplateRPC(v['host'], v['template'])
            if rpc != '':
                pass
                #TODO Schedule SNMP call here.
                #schedule.every(v['frequency']).seconds.do(self.poll, v['host'], rpc)
                #schedule.every(v['frequency']).seconds.do(self.executor.submit, self.poll, v['host'], rpc) #async call 


        print('SNMP polls scheduled.')


class databaseHandler:
    def __init__(self, data):
        self.DBUSER = config('DB_USER')
        self.DBPASS = config('DB_PASS')

        self.data = data

    def generateTable(self):
        pass


# Abstracts away the type of file host information is pulled from, I.e. application determines how to handle the file given same information. File extension is the determiner
class fileProcessor:

    def __init__(self, f=None):
        self.__f = f    # File w/path
        self.__hosts={} # Dict to run poll on

    def findFileType(self)->str:
        self.ftype=''

        #Determines what kind of file the user is using, returns filetype.
        if self.__f[-4:] == '.csv':
            self.ftype='csv'
        elif self.__f[-5:] == '.json':
            self.ftype='json'
        elif self.__f[-5:] == '.yaml':
            self.ftype='yaml'

        return self.ftype
    
    def readCSV(self)->dict:
        templatesToRun=[]
        try: 
            with open(self.__f) as inventory:
                invcsv = csv.reader(inventory)
                for row in invcsv:
                    if row == '':
                        continue
                    host = row[0]
                    freq = int(row[1])
                    templatesToRun = row[2:]
                    
                    hostDefinition = {
                            host:{
                            "frequency": freq,
                            "templates": templatesToRun
                            }
                    }
                    self.__hosts.update(hostDefinition)
        except IndexError as e:
            print(e)
            print('Problem occured at/after ', host, ' in hosts.csv.')

        
        #TODO Move this assertion to wherever this is called.
        assert dict == type(self.__hosts), "Read CSV should return type dict."
        # Return Dict
        return self.__hosts

    def readJSON(self):

        with open(self.__f) as f:
            self.__hosts = json.loads(f.read())

        #TODO Move this assertion to wherever this is called.
        assert dict == type(self.__hosts), "self.__hosts should return type dict."
        return self.__hosts

    def readYAML(self):
        pass

        #TODO Move this assertion to wherever this is called.
        assert dict == type(self.__hosts), "self.__hosts should return type dict."
        return self.__hosts


def start(f='hosts.csv'):
    #Initialize instance
    s = fileProcessor(f)
    ftype = s.findFileType()

    #Get host data: dict
    if ftype == 'csv':
        hosts = s.readCSV()
    elif ftype == 'json':
        hosts = s.readJSON()
    elif ftype == 'yaml':
        hosts = s.readYAML()
    else:
        print('No matching file type.')
        exit()
   
    p = protocolProcessor(hosts)
    p.getTemplateType()
    p.start_protocol()
    #p.startjobs()

    


if __name__ == ("__main__"):
    #start('x.json')
    start('hosts.csv')
