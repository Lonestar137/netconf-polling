from decouple import config
from ncclient import manager

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET
import schedule, csv, time, os, datetime

import psycopg2

def poll(USER, PASS, HOST, rpc):
    TIMESTAMP=str(datetime.datetime.now())

    try:
        #Connect to device
        eos = manager.connect(host=HOST, port='830', 
                timeout=5, username=USER, password=PASS, hostkey_verify=False)

        #Sends rpc to host, supports multple rpcs with ,, as delimiter.
        for i in rpc.split(',,'):
            if len(i) < 10:
                continue
            #Get xml root for parsing
            output=eos.get(filter=("subtree", i))
            root = ET.fromstring(str(output))

            print(HOST)
            #Define variables to retrieve here:
            #TODO Make this algorithm recursive so that it walks subtree better.
            for i in list(root[0][0][0]): 
                #i.tag is field name, i.text is field value
                output=str(i.tag.split('}')[1] + ':  '+ i.text)
                print('\t'+output)
            print('\n')

        eos.close_session()

    except Exception as e:
        print(str(e)+' for host: '+HOST)
        return 0

def conn_database(db_USER: str, db_PASS: str, DB: str, location: str = 'localhost')->object:
    #Connection to psql database opened
    db = "dbname="+DB+" user="+db_USER+" host="+location+" password="+db_PASS

    conn = psycopg2.connect(db)
    return conn

def create_tables_database(db_conn):
    #Takes templates dir templates and creates a table in db with same name.

def update_database(db_conn):
    cursor.execute("""""")



def schedule_from_csv(db_conn, file, USER: str, PASS: str):
    #Returns a str list of all FILES in the templates dir.  Dirs are ignored
    template_files = [f for f in listdir('./templates') if isfile(join('./templates', f))]
    
    #TODO Create tables from template names.
    try:
        create_tables_database(db_conn)
    except:
        pass

    with open(file) as inventory:
        invcsv = csv.reader(inventory)
        for row in invcsv:
            template=''
            host = row[0]
            freq = int(row[1])
            for mib in row[2:]:
                for template_name in template_files:
                    #For matching template found schedule rpc call
                    if mib == template_name:
                        with open('./templates/'+template_name, 'r') as f:#os.system('cat templates/'+template_name)
                            template+=f.read()+',,\n'

                    #If Template still empty and list finished
                    elif template=='' and template_name == template_files[len(template_files)-1]:
                        print('No matching template for '+mib+' on host '+ host +'.')
                        pass

            if template != '':
                schedule.every(freq).seconds.do(poll, USER, PASS, host, template)

def scheduler(db_connection, USER: str, PASS: str):

    #Schedule data collection
    schedule_from_csv(db_connection, 'hosts.csv', USER, PASS)

    #Schedule database update
    #TODO Run on separate Thread
    #schedule.every(freq).seconds.do(db_update, host, mib)

    #Run schedule
    while True:
        schedule.run_pending()



if __name__ == "__main__":
    user=config('NET_USER')
    passw=config('PASS')

    db_name = 'prime'
    db_host = 'localhost'
    db_user, db_pass = config('DB_USER'), config('DB_PASS')

    connection = conn_database(db_user, db_pass, db_name, db_host)
    cursor = connection.cursor()
    cursor.execute("""SELECT * FROM tutorial""")
    connection.commit()
    rows = cursor.fetchall()
    print(rows)
    cursor.close()
    #scheduler(connection, user, passw)



#TODO: schedule updates
#TODO: Whenever new template is created; creates a new table with that template name and 
#stores all the returned tags:values in teh table.


