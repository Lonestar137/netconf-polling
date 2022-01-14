
def server_request(user: str, password: str, server: str, payload: dict):
    #Returns a list of downed hosts
    s = requests.Session()
    requests.packages.urllib3.disable_warnings()
    s.trust_env = False
    response = s.post(server,
            verify=False,
            auth=(user, password),
            json=payload,
            headers={'Accept': 'application/json', 'X-HTTP-Method-Override': 'GET'}
            )
    return response.json()

def parse_dict(dt: dict):
    host_list=[]
    for group_tuple in dt.items():
        for x in group_tuple[1]:
            address=x['joins']['host']['address']
            try:
                geolocation=x['joins']['host']['vars']['geolocation']
                loc_x, loc_y=geolocation.split(',')
            except:
                pass
            host_list.append((address, loc_x, loc_y))
    return host_list
            
if __name__ == "__main__":
    #Retrieves GPS locations for devices from ICINGA and puts them in their own table.
    #Not necessary for netc to work.

    from netc import conn_database, create_tables_database, update_database
    from decouple import config
    import requests
    import schedule, time, datetime, psycopg2, csv

    #Get map information: 
    payload= {'joins': ['host.name', 'host.address', 'host.vars', 'host'],
            'attrs' : ['name', 'state', 'downtime_depth', 'acknowledgement'],
            }
#            'filter': 'match(host.vars.tenant, \"WC Region\")'}

    USER = config('MONITOR_USER')
    PASS = config('MONITOR_PASS')
    SERVER = config('MONITOR_URL')

    hosts = server_request(USER, PASS, SERVER, payload)
    parsed = parse_dict(hosts)#Returns host list [('host', 'xcord, ycord'), ...]
    #print(parsed)

    #Connect to db, and define columns to apply variables to
    db_name = 'grafana'
    db_host = 'localhost'
    db_user, db_pass = config('DB_USER'), config('DB_PASS')
    columns_to_create=' timestamp, IP VARCHAR, y_coord DOUBLE PRECISION, x_coord DOUBLE PRECISION, PRIMARY KEY (IP))'
    columns_to_update='( timestamp, IP, x_coord, y_coord)'

    #Find hosts in CSV, compare, to hosts in Icinga, return the Union
    hosts_to_render=[]
    with open('hosts.csv') as csv_file:
        csv_inv = csv.reader(csv_file)
        for row in csv_inv:
            host = row[0]
            for i in parsed:
                address=i[0]
                if address == host: 
                    hosts_to_render.append(address)
                    
    #Connect to database, create table geolocations if not exists, and plug in variables.
    with conn_database(db_user, db_pass, db_name, db_host) as connection:
        create_tables_database(connection, 'geolocations', '( TIMESTAMP '+columns_to_create)
        for i in parsed:
            address=i[0]
            if address in hosts_to_render:
                address="\'"+i[0]+"\'"
                x=i[1]
                y=i[2]
                values=' '+address+', '+x+', '+y+')'#Becomes (TIMESTAMP time.now(), IP, x, y)
                #print(values)
                try: 
                    update_database(connection, 'geolocations', str(datetime.datetime.now()),  columns_to_update, values)
                    connection.commit()
                except psycopg2.errors.UniqueViolation as e :
                    pass
                except psycopg2.errors.InFailedSqlTransaction as e:
                    pass

        


