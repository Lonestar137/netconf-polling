from decouple import config
from ncclient import manager

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET
import schedule, csv, time, os, datetime

import psycopg2

def poll(USER: str, PASS: str, HOST: str, rpc: str, template_file_names: list, db_connection: object):
    TIMESTAMP=str(datetime.datetime.now())
    index=0

    try:
        #Connect to device
        eos = manager.connect(host=HOST, port='830', 
                timeout=5, username=USER, password=PASS, hostkey_verify=False)

        #Sends rpc to host, supports multple rpcs with ,, as delimiter.
        for i in rpc.split(',,'):
            #skip empty
            if len(i) < 10:
                continue

            #Get xml root for parsing
            output=eos.get(filter=("subtree", i))
            root = ET.fromstring(str(output))

            print(HOST)
            columns="( timestamp DATE, "
            #Define variables to retrieve here:
            #TODO Make this algorithm recursive so that it walks subtree better.
            for i in list(root[0][0][0]): 
                #i.tag is field name, i.text is field value
                tag=str(i.tag.split('}')[1])
                text=str(i.text)
                #TODO Update database
                output=tag+':  '+text
                print('\t'+output)

                columns+=column_type_cast(tag, text)
            print('\n')

            columns=columns[:len(columns)-2]+");"

            #Curr rpc call template name
            template_name=template_file_names[index]
            create_tables_database(db_connection, template_name, columns)
            index+=1
        eos.close_session()

    except Exception as e:
        print(str(e)+' for host: '+HOST)
        return 0

    update_database(db_connection)


def column_type_cast(column, value)->str:
    #Replace unsupported chars for table names
    column=column.replace('-', '_')
    value=value.replace('-', '_')
    column=column.replace('/', '_')
    value=value.replace('/', '_')
    column=column.replace('\\', '_')
    value=value.replace('\\', '_')

    #Takes a string and assigns the required column type to it.
    try:
        #if field value is type int then make the column type int
        int(value)
        return column+" INT, "
    except:
        pass
    try:
        float(value)
        return column+" FLOAT, "
    except:
        pass

    #If nothing else make it a VARCHAR.
    return column+" VARCHAR(255), "
        
    


def conn_database(db_USER: str, db_PASS: str, DB: str, location: str = 'localhost')->object:
    #Connection to psql database opened
    db = "dbname="+DB+" user="+db_USER+" host="+location+" password="+db_PASS

    conn = psycopg2.connect(db)
    return conn

def create_tables_database(db_conn, template_name, table_columns):
    #Reads templates dir template names and creates a table in db with same name.

    cursor = db_conn.cursor()
    sql_cmd=("""CREATE TABLE if not exists """+template_name+table_columns)
    cursor.execute(sql_cmd)
    db_conn.commit()
    print(sql_cmd)

def update_database(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("""SELECT * FROM cell_radio;""")



def schedule_from_csv(db_conn, file, USER: str, PASS: str):
    #Returns a str list of all FILES in the templates dir.  Dirs are ignored
    template_files = [f for f in listdir('./templates') if isfile(join('./templates', f))]

    matched_templates=[]
    
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
                        #used for database table creation, t
                        matched_templates.append(mib)

                    #If Template still empty and list finished
                    elif template=='' and template_name == template_files[len(template_files)-1]:
                        print('No matching template for '+mib+' on host '+ host +'.')
                        pass

            if template != '':
                schedule.every(freq).seconds.do(poll, USER, PASS, host, template, matched_templates, db_conn)

def scheduler(db_connection,csv_file, USER: str, PASS: str):

    #Schedule data collection
    schedule_from_csv(db_connection, csv_file, USER, PASS)

    #Schedule database update
    #TODO Run on separate Thread
    #schedule.every(freq).seconds.do(db_update, host, mib)

    #Run schedule
    while True:
        schedule.run_pending()



if __name__ == "__main__":
    #Example usage of this file

    #User credentials for logging into polled devices.
    user=config('NET_USER')
    passw=config('PASS')
    
    #DB credentials and db host location
    db_name = 'grafana'
    db_host = 'localhost'
    db_user, db_pass = config('DB_USER'), config('DB_PASS')

    #Connection to db
    connection = conn_database(db_user, db_pass, db_name, db_host)

    #Schedule polling
    scheduler(connection, 'hosts.csv', user, passw)

    connection.close()



#TODO: schedule updates
#TODO: Whenever new template is created; creates a new table with that template name and 
#stores all the returned tags:values in teh table.


