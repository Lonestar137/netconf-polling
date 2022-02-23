from decouple import config
from netc import scheduler, conn_database
import threading
import queue



def job(csv_file):
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
    
    #TODO Schedule cleanup sql_cmd, (Deletes old data)


    #Schedule polling
    scheduler(connection, csv_file, user, passw)


    connection.close()

try:
    job('hosts.csv')
except Exception as e:
    print(e)
    pass


#thread1 = threading.Thread(target=job, args=("hosts.csv",))

#thread1.start()
