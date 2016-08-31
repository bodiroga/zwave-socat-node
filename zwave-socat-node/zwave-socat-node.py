#!/usr/bin/env python
import os
import sys
import time
import homie
import logging
import subprocess
logging.basicConfig(filename='/var/log/zwave-socat-node.log', format='%(asctime)s %(levelname)-8s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ZWAVE_PORT = "/dev/zwave"
SOCAT_PORT = 54321
REPORT_INTERVAL = 60 # seconds

try:
    Homie = homie.Homie("%s/configuration.json" % (os.path.dirname(os.path.realpath(__file__))))
except:
    logger.error("Configuration file doesn't exist or is not correctly defined")
    sys.exit(1)

socatNode = Homie.Node("socat", "socat")
timeNode = Homie.Node("time", "time")

def get_zwave_stick_status(zwave_stick_path):
    try:
        return os.path.exists(zwave_stick_path)
    except:
        return False

class SocatHandler(object):
    def __init__(self):
        self.process_id = None

    def start_local_socat(self):
        try:
            command = "/usr/bin/socat tcp-l:%s,reuseaddr,fork file:%s,raw,nonblock,echo=0" % (SOCAT_PORT, ZWAVE_PORT)
            result = subprocess.Popen(command.split(" "))
            self.process_id = result.pid
            logger.info("Local socat process started with pid: %s" % (self.process_id))
            return self.process_id
        except Exception as e:
            logger.error("start_local_socat error: %s" % e)
            return 0

    def kill_local_socat(self):
        try:
            command = "/usr/bin/killall socat"
            subprocess.Popen(command.split(" "))
            logger.info("Local socat process killed")
            return 1
        except Exception as e:
            logger.error("kill_local_socat error: %s" % e)
            return 0

def main():
    logger.info("Starting zwave-socat-node...")
    ip_connectivity = False
    old_stick_status = old_connection_status = None
    sc = SocatHandler()
    sc.kill_local_socat()
    Homie.setFirmware("zwave-socat-node", "1.0.0")
    while not ip_connectivity:
        try:
            Homie.setup()
            ip_connectivity = True
        except:
            logger.debug("No network connection yet")
            time.sleep(0.5)
    while (not Homie.mqtt_connected):
        time.sleep(0.1)

    Homie.setNodeProperty(socatNode, "port", SOCAT_PORT, True)
    Homie.setNodeProperty(timeNode, "last_report", int(time.time()), True)
    while True:
        new_stick_status = get_zwave_stick_status(ZWAVE_PORT)
        new_connection_status = Homie.mqtt_connected
        if old_stick_status != new_stick_status:
            logger.info("Stick state: %s" % (new_stick_status))
            Homie.setNodeProperty(socatNode, "status", str(new_stick_status).lower(), True)
            sc.start_local_socat() if new_stick_status else sc.kill_local_socat()
        if old_connection_status != new_connection_status:
            logger.info("MQTT state: %s" % (new_connection_status))
            Homie.setNodeProperty(socatNode, "status", str(new_stick_status).lower(), True)
        old_stick_status = new_stick_status
        old_connection_status = new_connection_status
        if int(time.time()) % REPORT_INTERVAL == 0:
            Homie.setNodeProperty(timeNode, "last_report", int(time.time()), True)   
        time.sleep(0.3)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Error: %s" % e)
