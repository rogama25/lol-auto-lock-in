import asyncio
import time
import logging

from lcu_driver.connection import Connection
import threading

from utils import MyConnector

connector = MyConnector()
logger = logging.getLogger("rogama-main")
logger.setLevel("DEBUG")
with open("example.log", "a+") as file:
    file.write("\n\n\n\n" + str(time.asctime()) + "\n")
logging.basicConfig(filename='example.log', level=logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)


def start():
    t = threading.Thread(target=connector.start)
    t.start()

@connector.ready
async def connect(connection: Connection):
    logger.info("Connected to LCU API")
    in_champion_select = False
    position = -1
    summ_request = await connection.request("get", "/lol-login/v1/session")
    summ_info = await summ_request.json()
    logger.debug(summ_info)
    acc_id = summ_info["summonerId"]
    logger.info("Summonner id is " + str(acc_id))
    while True:
        ch_select = await connection.request("get", "/lol-champ-select/v1/session")
        ch_select_info = await ch_select.json()
        logger.debug(ch_select_info)
        if "errorCode" in ch_select_info and in_champion_select:
            logger.info("No longer in champion select")
            position = -1
            in_champion_select = False
        if "errorCode" not in ch_select_info and not in_champion_select:
            logger.info("Entered champion select")
            in_champion_select = True
        if in_champion_select:
            for user in ch_select_info["myTeam"]:
                if user["summonerId"] == acc_id:
                    if position == -1:
                        logger.info("User position is " + str(user["cellId"]))
                    position = user["cellId"]
            for event_group in ch_select_info["actions"]:
                for event in event_group:
                    if event["actorCellId"] == position and event["type"] == "pick" and event["isInProgress"]:
                        event_id = event["id"]
                        timer = await connection.request("get", "/lol-champ-select/v1/session/timer")
                        timer_info = await timer.json()
                        logger.debug(timer_info)
                        current = time.time()
                        if "internalNowInEpochMs" in timer_info:
                            remaining = (timer_info["internalNowInEpochMs"]+timer_info["adjustedTimeLeftInPhase"])/1000-current
                            logger.info("Detected pick turn. Sleeping " + str(remaining - 0.75))
                            time.sleep(remaining-0.75)
                            lock_in = await connection.request("post", "/lol-champ-select/v1/session/actions/" +str(event_id)+ "/complete")
                            logger.info("Locked in.")
                        
        time.sleep(5)


@connector.close
async def disconnect(connection):
    logger.info("Disconnected from League")


def main():
    start()


if __name__ == "__main__":
    main()
