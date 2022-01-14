from decouple import config
from ncclient import manager

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET
import schedule, csv, time, os, datetime

import psycopg2
import logging

def poll(USER: str, PASS: str, HOST: str, rpc: str, template_file_names: list, db_connection: object):
    debug=config('DEBUG')

    #TIMESTAMP=str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    
    #There was a timezone issue with the EPOCH time being returned being different than the
    #converted timezone to UTC.  It was 6 hours behind.  
    #Note this may be different depending on your timezone you can change the hours= below to match the offset
    #in your rendered grafana data..
    fix_offset=datetime.timedelta(hours=6)
    TIMESTAMP=str(datetime.datetime.now()+fix_offset)
    #TODO LOGGING
    if debug == True:
        print(TIMESTAMP)
    index=0


    try:
        #Connect to device
        eos = manager.connect(host=HOST, port='830', 
                timeout=10, username=USER, password=PASS, hostkey_verify=False)

        #Sends rpc to host, supports multple rpcs with ,, as delimiter.
        for i in rpc.split(',,'):
            #skip empty rpc
            if len(i) < 10:
                continue

            #Get xml root for parsing, i.e (The returned output of the rpc call to device.)
            output=eos.get(filter=("subtree", i))
            root = ET.fromstring(str(output))

            if debug == 'True':
                print(HOST)

            #Generate sql cmd parameters
            columns="( timestamp TIMESTAMP, IP varchar(255), "
            columns_to_update="(timestamp, IP, "

            #Start of update query, finished in update_db function.
            update_values="'"+HOST+"', "

            #Define variables to retrieve here:
            #TODO Make this algorithm recursive so that it walks subtree better.
            for i in list(root[0][0][0]): 
                #i.tag is field name, i.text is field value
                tag=str(i.tag.split('}')[1])
                text=str(i.text)
                
                #For logging purposes
                #TODO LOGGING
                output=tag+':  '+text
                if debug == 'True':
                    print('\t'+output)

                #For table creation, creates sql command, assigns sql column types
                formated_tag, formated_text=column_type_cast(tag, text)
                columns+=formated_tag

                #For update sql command, i.e. INSERT INTO TABLE(columns_to_update) Values (update_values)
                columns_to_update+=tag+", "
                update_values+=formated_text+", "
            
            #TODO LOGGING
            if debug == 'True':
                print('\n')

            #Remove trailing ,
            columns=columns[:len(columns)-2]+");"
            #columns+="PRIMARY KEY (timestamp));"

            columns_to_update=columns_to_update[:len(columns_to_update)-2]+")"
            update_values=update_values[:len(update_values)-2]+");"

            #Curr rpc call template name
            template_name=template_file_names[index]
            create_tables_database(db_connection, template_name, columns)
            index+=1

            update_database(db_connection, template_name, TIMESTAMP, columns_to_update, update_values)
        eos.close_session()

    except Exception as e:
        #TODO LOGGING
        if debug == 'True':
            print(str(e)+' for host: '+HOST)
        return 0



def column_type_cast(column, value)->str:
    #Replace unsupported chars for table names
    value=remove_unsupported_chars(value)
    column=remove_unsupported_chars(column)
    column=column.replace('-', '_')

    #Takes a string and assigns the required column type to it.
    try:
        #if field value is type int then make the column type int
        int(value)
        return column+" INT, ", value
    except:
        pass
    try:
        float(value)
        return column+" FLOAT, ", value
    except:
        pass

    #If nothing else make it a VARCHAR, and format the value for VARCHAR
    return column+" VARCHAR(255), ", "'"+value+"'"
        
    


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

def update_database(db_conn, table_name, timestamp, columns, values):
    #Replace unsupported chars for table names
    columns=remove_unsupported_chars(columns)
    columns=columns.replace('-', '_')

    values=remove_unsupported_chars(values)
    
    #TODO Replace with f string format
    #Complete values query parameters.
    values="( TIMESTAMP '"+timestamp+"', "+values

    cursor = db_conn.cursor()
    sql_update_cmd="INSERT INTO "+table_name+columns+" VALUES"+values
    #print(sql_update_cmd)
    cursor.execute(sql_update_cmd)

def remove_unsupported_chars(string: str):
    #string=string.replace('-', '_')
    string=string.replace('/', '_')
    string=string.replace('\\', '_')
    return string


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
                    #For matching template found in templates dir schedule rpc call
                    if mib == template_name:
                        with open('./templates/'+template_name, 'r') as f:
                            #,, delimits rpc calls
                            template+=f.read()+',,\n'

                        #array used for database table creation, t
                        matched_templates.append(mib)

                    #If template var still empty and list finished, then the mib described in hosts.csv for that device cannot be found in templates dir
                    elif template=='' and template_name == template_files[len(template_files)-1]:
                        #TODO f format string
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
    #Setup logging
    #logging.basicConfig(filename='./logs/poll.log', encoding='utf-8', level=logging.DEBUG)

    #User credentials for logging into polled devices.
    user=config('NET_USER')
    passw=config('PASS')
    
    #DB credentials and db host location
    db_name = 'grafana'
    db_host = 'localhost'
    db_user, db_pass = config('DB_USER'), config('DB_PASS')

    #Connection to db
    connection = conn_database(db_user, db_pass, db_name, db_host)
    
    #TODO Schedule cleanup sql_query

    #Schedule polling
    scheduler(connection, 'hosts.csv', user, passw)

    connection.close()



#TODO: schedule updates
#TODO: Whenever new template is created; creates a new table with that template name and 
#stores all the returned tags:values in teh table.


