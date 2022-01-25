from decouple import config
from netc import scheduler, conn_database
import threading




def nc_region():
    pass


def ec_region(csv_file):
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
    scheduler(connection, csv_file, user, passw)

    connection.close()

def hello(test):
    print(test)


#nc_region()
thread1 = threading.Thread(target=ec_region, args=("ec_region.csv",))

thread1.start()
