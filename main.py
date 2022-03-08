from decouple import config
#from netc import scheduler, conn_database
import netc
import threading
import queue




netc.start('hosts.csv')
