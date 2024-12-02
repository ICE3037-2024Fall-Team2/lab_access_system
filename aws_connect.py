import pymysql

def connect_to_rds():
    try:
        conn = pymysql.connect(
                           
        )
        return conn
    except pymysql.MySQLError as e:
        raise Exception(f"Failed to connect to RDS: {str(e)}")
