#!/usr/bin/python3

import cfnresponse 
import pymysql
import logging
import threading

def timeout(event, context):
    logging.error('Execution is about to time out, sending failure response to CloudFormation')
    cfnresponse.send(event, context, cfnresponse.FAILED, {})
                
def handler(event, context): 
    status = cfnresponse.SUCCESS
    timer = threading.Timer((context.get_remaining_time_in_millis()
                        / 1000.00) - 0.5, timeout, args=[event, context])
    timer.start()
    
    try:   
        if event['RequestType'] == 'Create':
            fe_leader_ip = event['ResourceProperties']['FeLeaderInstancePrivateIp'] 
            root_password = event['ResourceProperties']['RootPassword']
            password  = '' if event["ResourceType"] == "Custom::ChangeRootPassword" else root_password 
            db = pymysql.connect(host=fe_leader_ip, user='root', password=password, port=9030)
            cursor = db.cursor()

            if event["ResourceType"] == "Custom::ChangeRootPassword":
                cursor.execute(f"SET PASSWORD for root = PASSWORD('{root_password}');")   
            if event["ResourceType"] == "Custom::AddBE":
                for i in range(1, 7):
                    if event['ResourceProperties'].get("BeInstance" + str(i) + "PrivateIp", ""):
                        be_ip = event['ResourceProperties']["BeInstance" + str(i) + "PrivateIp"]
                        cursor.execute(f"ALTER SYSTEM ADD BACKEND '{be_ip}:9050'")
            if event["ResourceType"] == "Custom::AddFEFollower":
                for i in range(1, 3):
                    if event['ResourceProperties'].get("FeFollowerInstance" + str(i) + "PrivateIp", ""):
                        follower_ip = event['ResourceProperties']["FeFollowerInstance" + str(i) + "PrivateIp"]
                        cursor.execute(f"ALTER SYSTEM ADD FOLLOWER '{follower_ip}:9010'")                        
            db.close()
    except Exception as e:
        logging.error('Exception: %s' % e, exc_info=True)
        status = cfnresponse.FAILED
    finally:
        timer.cancel()
        cfnresponse.send(event, context, status, {})